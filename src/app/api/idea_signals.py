from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Header, Request, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import CallerContextHeaders
from app.api.durable_write_guard import (
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.idea_signal_models import (
    CandidatePersistenceSummaryResponse,
    EvaluateAndPersistHighCashSignalResponse,
    EvaluateHighCashFromSourceRequest,
    EvaluateHighCashSignalRequest,
    EvaluateHighCashSignalResponse,
    EvaluateMandateRestrictionFromSourceRequest,
    EvaluateMandateRestrictionSignalRequest,
    EvaluateMandateRestrictionSignalResponse,
)
from app.api.runtime_dependencies import (
    AdvisePolicyEvaluationSourceRuntime,
    AdvisePolicyEvaluationSourceRuntimeBlocker,
    CoreHighCashSourceRuntime,
    CoreHighCashSourceRuntimeBlocker,
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.runtime_dependencies import (
    build_advise_policy_evaluation_source_runtime_from_environment as _build_advise_policy_evaluation_source_runtime_from_environment,
)
from app.api.runtime_dependencies import (
    build_core_high_cash_source_runtime_from_environment as _build_core_high_cash_source_runtime_from_environment,
)
from app.api.signal_api_support import (
    RouteMetadata,
    SignalSourceRefContract,
    evaluate_caller_supplied_signal,
    evaluate_source_signal,
    operation_outcome_from_signal_evaluation,
    signal_problem_responses,
    signal_source_ref_contract_problem_or_none,
    source_authority_from_contracts,
)
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    evaluate_high_cash_signal_from_core,
    evaluate_high_cash_signal_command,
)
from app.application.access_scope import portfolio_only_scope
from app.application.high_cash_signal import (
    evaluate_and_persist_high_cash_signal as evaluate_and_persist_high_cash_signal_command,
)
from app.application.mandate_restriction_signal import (
    evaluate_mandate_restriction_signal_from_advise,
    evaluate_mandate_restriction_signal_command,
)
from app.domain import (
    CandidatePersistenceDecision,
    SignalEvaluationResult,
    SourceSystem,
)
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    permission_denied_metadata,
    problem_details_response as problem_response,
    service_unavailable_metadata,
)
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)


def _is_core_high_cash_runtime_blocked(
    runtime: object,
) -> bool:
    return isinstance(runtime, CoreHighCashSourceRuntimeBlocker)


def _is_advise_policy_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, AdvisePolicyEvaluationSourceRuntimeBlocker)


_PERSIST_HIGH_CASH_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.candidate.persist",
)


_MANDATE_RESTRICTION_PRODUCT_IDS_BY_SOURCE: dict[SourceSystem, tuple[str, ...]] = {
    SourceSystem.LOTUS_CORE: ("lotus-core:PortfolioStateSnapshot:v1",),
    SourceSystem.LOTUS_MANAGE: ("lotus-manage:PortfolioActionRegister:v1",),
    SourceSystem.LOTUS_ADVISE: ("lotus-advise:AdvisoryPolicyEvaluationRecord:v1",),
}


async def evaluate_high_cash_signal(
    request: EvaluateHighCashSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateHighCashSignalResponse | JSONResponse:
    source_authority = _high_cash_source_authority(request)
    source_contracts = _high_cash_source_ref_contracts(request)
    return evaluate_caller_supplied_signal(
        caller=caller,
        source_authority=source_authority,
        source_contracts=source_contracts,
        requested_access_scope=(
            request.access_scope.to_domain() if request.access_scope is not None else None
        ),
        command_factory=request.to_command,
        evaluator=evaluate_high_cash_signal_command,
        response_factory=EvaluateHighCashSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_high_cash_signal_from_source(
    request: Request,
    signal_request: EvaluateHighCashFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateHighCashSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_CORE.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        runtime_factory=_build_core_high_cash_source_runtime_from_environment,
        is_runtime_blocked=_is_core_high_cash_runtime_blocked,
        blocked_detail="Core source runtime is not configured for high-cash source evaluation.",
        command_factory=lambda runtime, tenant_id: signal_request.to_command(
            tenant_id=tenant_id or "",
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_high_cash_signal_from_core(
            command,
            core_source=cast(CoreHighCashSourceRuntime, runtime).core_source,
        ),
        response_factory=EvaluateHighCashSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
        require_tenant_context=True,
    )


async def evaluate_mandate_restriction_signal(
    request: EvaluateMandateRestrictionSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMandateRestrictionSignalResponse | JSONResponse:
    source_contracts = _mandate_restriction_source_ref_contracts(request)
    source_authority = _mandate_restriction_source_authority(request)
    return evaluate_caller_supplied_signal(
        caller=caller,
        source_authority=source_authority,
        source_contracts=source_contracts,
        requested_access_scope=(
            request.access_scope.to_domain() if request.access_scope is not None else None
        ),
        command_factory=request.to_command,
        evaluator=evaluate_mandate_restriction_signal_command,
        response_factory=EvaluateMandateRestrictionSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
        contract_mode="one_of",
    )


async def evaluate_mandate_restriction_signal_from_source(
    request: Request,
    signal_request: EvaluateMandateRestrictionFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateMandateRestrictionSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_ADVISE.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=(
            signal_request.access_scope.to_domain()
            if signal_request.access_scope is not None
            else None
        ),
        runtime_factory=_build_advise_policy_evaluation_source_runtime_from_environment,
        is_runtime_blocked=_is_advise_policy_runtime_blocked,
        blocked_detail="Advise source runtime is not configured for mandate-restriction source evaluation.",
        command_factory=lambda runtime, _tenant_id: signal_request.to_command(
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_mandate_restriction_signal_from_advise(
            command,
            advise_source=cast(AdvisePolicyEvaluationSourceRuntime, runtime).advise_source,
        ),
        response_factory=EvaluateMandateRestrictionSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_and_persist_high_cash_signal(
    request: EvaluateHighCashSignalRequest,
    caller: CallerContextHeaders,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> EvaluateAndPersistHighCashSignalResponse | JSONResponse:
    try:
        require_capability(caller, _PERSIST_HIGH_CASH_POLICY)
    except PermissionDeniedError:
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.PERMISSION_DENIED,
            source_authority="lotus-core",
            error_code="permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to persist idea candidates.",
        )
    if not idempotency_key.strip():
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.INVALID_REQUEST,
            source_authority="lotus-core",
            error_code="invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Idempotency-Key is required.",
        )

    source_authority = _high_cash_source_authority(request)
    source_contracts = _high_cash_source_ref_contracts(request)
    contract_problem = signal_source_ref_contract_problem_or_none(
        contracts=source_contracts,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if contract_problem is not None:
        return contract_problem
    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.BLOCKED,
            source_authority=source_authority,
            durable_storage_backed=durable_storage_backed,
            error_code="durable_repository_not_configured",
        )
        return configuration_problem
    result = evaluate_and_persist_high_cash_signal_command(
        EvaluateAndPersistHighCashSignalCommand(
            evaluation=request.to_command(),
            idempotency_key=idempotency_key,
            actor_subject=caller.subject,
        ),
        repository=repository,
    )
    if (
        result.persistence is not None
        and result.persistence.decision is CandidatePersistenceDecision.CONFLICT
    ):
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.CONFLICT,
            source_authority="lotus-core",
            durable_storage_backed=durable_storage_backed,
            error_code="idempotency_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )

    emit_foundation_operation_event(
        IdeaOperation.CANDIDATE_PERSISTENCE,
        _operation_outcome_from_candidate_persistence(
            persistence_decision=(
                result.persistence.decision if result.persistence is not None else None
            ),
            evaluation=result.evaluation,
        ),
        source_authority=source_authority,
        durable_storage_backed=durable_storage_backed,
    )
    return EvaluateAndPersistHighCashSignalResponse(
        evaluation=EvaluateHighCashSignalResponse.from_domain(
            result.evaluation,
            source_authority=source_authority,
        ),
        persistence=(
            CandidatePersistenceSummaryResponse.from_record(
                decision=result.persistence.decision,
                record=result.persistence.record,
            )
            if result.persistence is not None
            else None
        ),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _operation_outcome_from_candidate_persistence(
    *,
    persistence_decision: CandidatePersistenceDecision | None,
    evaluation: SignalEvaluationResult,
) -> OperationOutcome:
    if persistence_decision is None:
        return operation_outcome_from_signal_evaluation(evaluation)
    if persistence_decision is CandidatePersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if persistence_decision is CandidatePersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if persistence_decision is CandidatePersistenceDecision.DUPLICATE_CANDIDATE:
        return OperationOutcome.DUPLICATE
    return OperationOutcome.CONFLICT


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


def _high_cash_source_authority(request: EvaluateHighCashSignalRequest) -> str:
    return source_authority_from_contracts(_high_cash_source_ref_contracts(request))


def _mandate_restriction_source_authority(
    request: EvaluateMandateRestrictionSignalRequest,
) -> str:
    source_ref = request.restriction_ref
    if (
        source_ref is not None
        and source_ref.source_system in _MANDATE_RESTRICTION_PRODUCT_IDS_BY_SOURCE
    ):
        return source_ref.source_system.value
    return source_authority_from_contracts(_mandate_restriction_source_ref_contracts(request))


def _high_cash_source_ref_contracts(
    request: EvaluateHighCashSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    evidence = request.source_evidence
    return (
        SignalSourceRefContract(
            evidence.portfolio_state_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioStateSnapshot:v1",),
        ),
        SignalSourceRefContract(
            evidence.holdings_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:HoldingsAsOf:v1",),
        ),
        SignalSourceRefContract(
            evidence.cash_movement_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioCashMovementSummary:v1",),
        ),
        SignalSourceRefContract(
            evidence.cashflow_projection_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioCashflowProjection:v1",),
        ),
    )


def _mandate_restriction_source_ref_contracts(
    request: EvaluateMandateRestrictionSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return tuple(
        SignalSourceRefContract(
            request.restriction_ref,
            source_system,
            product_ids,
        )
        for source_system, product_ids in _MANDATE_RESTRICTION_PRODUCT_IDS_BY_SOURCE.items()
    )


HIGH_CASH_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-cash/evaluate",
    "operation_id": "evaluateHighCashIdeaSignal",
    "summary": "Evaluate a high-cash idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core evidence for the first high-cash "
        "opportunity family. The endpoint is a certified API foundation for RFC-0002 Slice 10; "
        "it does not fetch upstream sources, certify a data product, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateHighCashSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "High-cash signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "high_cash",
                        "reasonCodes": [
                            "high_cash_ratio",
                            "cash_source_ready",
                            "review_required",
                        ],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "82",
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-core",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-cash/evaluate-from-source",
    "operation_id": "evaluateHighCashIdeaSignalFromSource",
    "summary": "Evaluate a high-cash idea signal from Core",
    "description": (
        "Fetches source-owned high-cash evidence through the configured Core source "
        "adapter, then evaluates deterministic high-cash candidate posture. The endpoint "
        "does not persist candidates, calculate cash weight locally, certify live source "
        "support, create Gateway/Workbench support, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateHighCashSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Core-backed high-cash signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "high_cash",
                        "reasonCodes": [
                            "high_cash_ratio",
                            "cash_source_ready",
                            "review_required",
                        ],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "82",
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-core",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Core source runtime is not configured for high-cash source evaluation.",
            description="Core source runtime configuration is missing or invalid.",
        ),
    },
}


MANDATE_RESTRICTION_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/mandate-restriction/evaluate",
    "operation_id": "evaluateMandateRestrictionIdeaSignal",
    "summary": "Evaluate a mandate or restriction idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core, Manage, or Advise evidence for "
        "mandate, restriction, or suitability-policy review posture. The endpoint is a "
        "bounded API foundation; it does not fetch upstream sources, approve suitability, "
        "change a mandate, clear a restriction, publish client communication, or promote a "
        "supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMandateRestrictionSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Mandate/restriction signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "mandate_restriction",
                        "reasonCodes": [
                            "mandate_restriction_review",
                            "review_required",
                        ],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_mandate_restriction_8d57adbf52f7f5a7",
                            "family": "mandate_restriction",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "compliance_review_required",
                            "evidencePacketId": "iep_mandate_restriction_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "66",
                            "scorePolicyVersion": "mandate-restriction-review-v1",
                            "sourceSignalIds": ["signal_mandate_restriction_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                                    "sourceSystem": "lotus-advise",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "quality_passed",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-advise",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/mandate-restriction/evaluate-from-source",
    "operation_id": "evaluateMandateRestrictionIdeaSignalFromSource",
    "summary": "Evaluate a mandate or restriction idea signal from Lotus Advise",
    "description": (
        "Fetches source-owned Lotus Advise policy-evaluation workflow posture "
        "through the configured Advise source adapter, then evaluates deterministic "
        "mandate/restriction review posture only when Advise emits explicit "
        "restriction diagnostic evidence. The endpoint does not persist candidates, "
        "clear restrictions, change mandate state, approve suitability, approve "
        "policy, approve proposals, create rebalance or order authority, publish "
        "client communication, certify live source support, create Gateway/Workbench "
        "support, certify a typed restriction data product, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMandateRestrictionSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: MANDATE_RESTRICTION_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Advise source runtime is not configured for mandate-restriction source evaluation.",
            description="Advise source runtime configuration is missing or invalid.",
        ),
    },
}


HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-cash/evaluate-and-persist",
    "operation_id": "evaluateAndPersistHighCashIdeaSignal",
    "summary": "Evaluate and persist a high-cash idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core evidence for the first high-cash "
        "opportunity family, then persists created candidates through the internal "
        "idempotency/audit repository foundation. The endpoint is an internal certified "
        "API foundation; local/test profiles may use process-local writes, while "
        "production-like profiles require LOTUS_IDEA_DATABASE_URL and fail closed before "
        "in-memory mutation. No supported business feature is promoted."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateAndPersistHighCashSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "High-cash signal evaluation completed and candidate persistence accepted, replayed, duplicated, or skipped for non-created candidates.",
            "content": {
                "application/json": {
                    "example": {
                        "evaluation": {
                            "outcome": "candidate_created",
                            "family": "high_cash",
                            "reasonCodes": [
                                "high_cash_ratio",
                                "cash_source_ready",
                                "review_required",
                            ],
                            "unsupportedReasons": [],
                            "candidate": {
                                "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                                "family": "high_cash",
                                "lifecycleStatus": "generated",
                                "reviewPosture": "advisor_review_required",
                                "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                                "supportability": "ready",
                                "score": "82",
                                "scorePolicyVersion": "idle-liquidity-v1",
                                "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                                "sourceRefs": [
                                    {
                                        "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                        "sourceSystem": "lotus-core",
                                        "productVersion": "v1",
                                        "asOfDate": "2026-06-21",
                                        "generatedAtUtc": "2026-06-21T10:00:00Z",
                                        "dataQualityStatus": "complete",
                                        "freshness": "current",
                                    }
                                ],
                            },
                            "sourceAuthority": "lotus-core",
                            "supportedFeaturePromoted": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidenceHash": "sha256:evidence-hash",
                            "persistedAtUtc": "2026-06-21T10:00:00Z",
                            "auditEventType": "idea.candidate.persisted",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Request validation failed. Correct the request fields and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to persist idea candidates.",
            description="Caller lacks the required candidate-persistence capability.",
        ),
        **conflict_metadata(
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
            description="The idempotency key was already used with a different request payload.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_idea_signal_routes(app: FastAPI) -> None:
    app.post(
        path=HIGH_CASH_EVALUATE_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_ROUTE["responses"],
    )(evaluate_high_cash_signal)
    app.post(
        path=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_high_cash_signal_from_source)
    app.post(
        path=MANDATE_RESTRICTION_EVALUATE_ROUTE["path"],
        operation_id=MANDATE_RESTRICTION_EVALUATE_ROUTE["operation_id"],
        summary=MANDATE_RESTRICTION_EVALUATE_ROUTE["summary"],
        description=MANDATE_RESTRICTION_EVALUATE_ROUTE["description"],
        status_code=MANDATE_RESTRICTION_EVALUATE_ROUTE["status_code"],
        response_model=MANDATE_RESTRICTION_EVALUATE_ROUTE["response_model"],
        tags=MANDATE_RESTRICTION_EVALUATE_ROUTE["tags"],
        responses=MANDATE_RESTRICTION_EVALUATE_ROUTE["responses"],
    )(evaluate_mandate_restriction_signal)
    app.post(
        path=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_mandate_restriction_signal_from_source)
    app.post(
        path=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["responses"],
    )(evaluate_and_persist_high_cash_signal)
