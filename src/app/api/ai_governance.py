from __future__ import annotations

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse

from app.api.ai_governance_models import (
    AIExplanationEvaluationRequest,
    AIExplanationEvaluationResponse,
    AIExplanationReadinessResponse,
    AIOutputClaimRequest,
    AIProposedActionRequest,
    AIWorkflowOutputRequest,
    AIWorkflowOutputSummaryResponse,
    AIWorkflowPackRequest,
    AIWorkflowPackResponse,
    RedactedIdeaEvidenceResponse,
    RedactedSourceRefResponse,
)
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.durable_write_guard import (
    DURABLE_REPOSITORY_NOT_CONFIGURED,
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    merged_problem_response_metadata,
    not_found_metadata,
    permission_denied_metadata,
    problem_response_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.ai_governance import (
    AIExplanationEvaluationDecision,
    AIExplanationWorkflowResult,
    build_ai_explanation_readiness_snapshot,
    evaluate_ai_explanation_to_repository,
)
from app.domain import (
    AIExplanationLineagePersistenceDecision,
    AIExplanationPosture,
    AIExplanationResult,
    InvalidAIExplanationRequest,
    InvalidAIWorkflowPack,
    InvalidAIWorkflowOutput,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_foundation_operation_event,
    emit_operation_event,
)
from app.security.caller_context import CallerContext, PermissionDeniedError

_AI_EXPLANATION_CAPABILITY = "idea.ai-explanation.evaluate"
_AI_EXPLANATION_READINESS_CAPABILITY = "idea.ai-explanation.readiness.read"


async def get_ai_explanation_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> AIExplanationReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        _require_ai_explanation_readiness_caller(caller)
    except PermissionDeniedError:
        _emit_ai_explanation_readiness_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea AI explanation readiness.",
        )

    repository = get_idea_repository()
    snapshot = build_ai_explanation_readiness_snapshot(
        durable_ai_lineage_store_backed=idea_repository_durable_storage_backed(repository)
    )
    _emit_ai_explanation_readiness_operation_event(
        OperationOutcome.BLOCKED,
        durable_storage_backed=snapshot.durable_ai_lineage_store_backed,
    )
    return AIExplanationReadinessResponse.from_domain(snapshot)


async def evaluate_ai_explanation(
    request: AIExplanationEvaluationRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> AIExplanationEvaluationResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        _require_ai_explanation_caller(caller)
        validate_idempotency_key(idempotency_key)
        command = request.to_command(
            candidate_id=candidate_id,
            caller=caller,
            idempotency_key=idempotency_key,
        )
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        configuration_problem = durable_write_problem(repository)
        if configuration_problem is not None:
            _emit_ai_explanation_operation_event(
                OperationOutcome.BLOCKED,
                DURABLE_REPOSITORY_NOT_CONFIGURED,
                durable_storage_backed=durable_storage_backed,
            )
            return configuration_problem
        result = evaluate_ai_explanation_to_repository(
            command,
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_ai_explanation_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea AI explanations.",
        )
    except InvalidAIWorkflowOutput:
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_ai_output",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_ai_output",
            title="Invalid AI output",
            detail="The AI workflow output does not match the governed explanation request.",
        )
    except InvalidAIWorkflowPack:
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_ai_workflow_pack",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_ai_workflow_pack",
            title="Invalid AI workflow pack",
            detail="Use the registered Lotus AI idea explanation workflow pack contract.",
        )
    except InvalidAIExplanationRequest as exc:
        return _invalid_ai_explanation_request_response(exc)
    except ValueError:
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the AI explanation evaluation request and retry.",
        )

    problem = _ai_explanation_result_problem(result)
    if problem is not None:
        return problem
    assert result.explanation_result is not None
    assert result.lineage_persistence_result is not None
    _emit_ai_explanation_operation_event(
        _operation_outcome_from_ai_result(result.explanation_result)
    )
    return AIExplanationEvaluationResponse.from_domain(
        result.explanation_result,
        ai_lineage_recorded=result.lineage_persistence_result.lineage_record is not None,
        ai_lineage_persistence_decision=result.lineage_persistence_result.decision.value,
        durable_storage_backed=bool(getattr(repository, "durable_storage_backed", False)),
    )


def _ai_explanation_result_problem(
    result: AIExplanationWorkflowResult,
) -> JSONResponse | None:
    if result.decision is AIExplanationEvaluationDecision.NOT_FOUND:
        _emit_ai_explanation_operation_event(OperationOutcome.NOT_FOUND, "candidate_not_found")
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    if result.decision is AIExplanationEvaluationDecision.IDEMPOTENCY_CONFLICT:
        _emit_ai_explanation_operation_event(OperationOutcome.CONFLICT, "idempotency_conflict")
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    if result.lineage_persistence_result is None:
        return None
    if (
        result.lineage_persistence_result.decision
        is AIExplanationLineagePersistenceDecision.CONFLICT
    ):
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_STATE,
            "ai_explanation_lineage_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="ai_explanation_lineage_conflict",
            title="AI explanation lineage conflict",
            detail="The AI explanation request id has already been recorded with different lineage.",
        )
    if (
        result.lineage_persistence_result.decision
        is AIExplanationLineagePersistenceDecision.NOT_FOUND
    ):
        _emit_ai_explanation_operation_event(OperationOutcome.NOT_FOUND, "candidate_not_found")
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    return None


def _require_ai_explanation_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_AI_EXPLANATION_CAPABILITY):
        raise PermissionDeniedError(_AI_EXPLANATION_CAPABILITY)


def _require_ai_explanation_readiness_caller(caller: CallerContext) -> None:
    if not caller.has_role("operator") or not caller.has_capability(
        _AI_EXPLANATION_READINESS_CAPABILITY
    ):
        raise PermissionDeniedError(_AI_EXPLANATION_READINESS_CAPABILITY)


def _invalid_ai_explanation_request_response(exc: InvalidAIExplanationRequest) -> JSONResponse:
    message = str(exc)
    if message.startswith("rationale drafting requires"):
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_STATE,
            "ai_explanation_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="ai_explanation_conflict",
            title="AI explanation conflict",
            detail="The requested AI explanation purpose is not valid for the current candidate state.",
        )
    _emit_ai_explanation_operation_event(
        OperationOutcome.INVALID_REQUEST,
        "invalid_request",
    )
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Correct the AI explanation evaluation request and retry.",
    )


def _operation_outcome_from_ai_result(result: AIExplanationResult) -> OperationOutcome:
    if result.posture is AIExplanationPosture.READY_FOR_ADVISOR_REVIEW:
        return OperationOutcome.ACCEPTED
    if result.posture is AIExplanationPosture.FALLBACK_USED:
        return OperationOutcome.FALLBACK
    return OperationOutcome.BLOCKED


def _emit_ai_explanation_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.AI_EXPLANATION,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


def _emit_ai_explanation_readiness_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.AI_EXPLANATION_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-ai",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


AI_EXPLANATION_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/ai-explanations/readiness",
    "operation_id": "getIdeaAIExplanationReadiness",
    "summary": "Get AI explanation readiness",
    "description": (
        "Returns source-safe operator readiness for the internal AI explanation foundation. "
        "The endpoint reports guardrail availability, the versioned deterministic action-content "
        "policy, and certification blockers only. Forbidden-action blocking covers structured "
        "types and untrusted label content; accepted labels are server-owned. It does "
        "not invoke lotus-ai runtime workflows, expose prompts or provider payloads, disclose "
        "candidate evidence, grant downstream authority, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AIExplanationReadinessResponse,
    "tags": ["Operations", "Idea AI Governance"],
    "responses": {
        200: {
            "description": "AI explanation readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "sourceAuthority": "lotus-idea",
                        "workflowAuthority": "lotus-ai",
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "deterministicFallbackAvailable": True,
                        "verifierAvailable": True,
                        "redactedEvidenceEnvelopeAvailable": True,
                        "unsupportedClaimBlockingAvailable": True,
                        "forbiddenActionBlockingAvailable": True,
                        "actionContentPolicyVersion": ("lotus-idea.ai-action-content-policy.v1"),
                        "durableAiLineageStoreBacked": False,
                        "modelRiskOperationsContractAvailable": True,
                        "modelRiskDashboardContractAvailable": True,
                        "modelRiskAlertContractAvailable": True,
                        "modelRiskDashboardCertified": True,
                        "modelRiskAlertCertified": True,
                        "lotusAiRuntimeExecuted": False,
                        "certificationBlockers": [
                            "lotus_ai_runtime_execution_missing",
                            "certified_ai_lineage_store_missing",
                            "workflow_pack_runtime_contract_not_certified",
                            "certified_runtime_trust_telemetry_missing",
                            "workbench_product_proof_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller is not permitted to read AI explanation readiness.",
            description="Caller lacks AI explanation readiness permission.",
        ),
    },
}


AI_EXPLANATION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
    "operation_id": "evaluateIdeaAIExplanation",
    "summary": "Evaluate an idea AI explanation",
    "description": (
        "Evaluates an internal AI explanation workflow result or deterministic fallback "
        "against a persisted idea candidate. The route applies redaction, source-product "
        "claim verification, forbidden-action blocking, source-safe lineage recording, "
        "versioned output-content integrity, "
        "API Idempotency-Key replay/conflict protection, and bounded operation telemetry. "
        "It does not call an AI provider, execute lotus-ai runtime workflows, persist "
        "provider payloads or prompts, grant downstream authority, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AIExplanationEvaluationResponse,
    "tags": ["Idea AI Governance"],
    "responses": {
        200: {
            "description": "AI explanation evaluation returned through the internal foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "requestId": "ai-explanation-001",
                        "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                        "workflowPack": {
                            "workflowPackId": "lotus-ai:idea-explanation:v1",
                            "workflowPackVersion": "v1",
                            "purpose": "advisor_rationale_draft",
                            "evaluationRef": "lotus-ai:governed-verifier:v1",
                            "sourceAuthority": "lotus-ai",
                        },
                        "posture": "ready_for_advisor_review",
                        "verifierOutcome": "passed",
                        "explanationText": (
                            "Candidate has elevated idle cash and source-ready evidence "
                            "for advisor review."
                        ),
                        "reasonCodes": ["ai_verifier_passed"],
                        "fallbackUsed": False,
                        "fallbackReason": None,
                        "grantsDownstreamAuthority": False,
                        "auditEventType": "idea.ai_explanation.evaluated",
                        "outputIntegrityVersion": "lotus-idea.ai-output-integrity.v1",
                        "outputContentDigest": f"sha256:{'a' * 64}",
                        "redactedEvidence": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "ready_for_review",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "evidenceContentHash": "sha256:evidence-lineage",
                            "supportability": "ready",
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "freshness": "current",
                                    "dataQualityStatus": "complete",
                                }
                            ],
                            "reasonCodes": ["high_cash_ratio", "review_required"],
                            "unsupportedReasons": [],
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "score": "82",
                            "sourceSignalCount": 1,
                        },
                        "verifiedOutput": {
                            "outputId": "ai-output-001",
                            "claimIds": ["claim-001"],
                            "proposedActionTypes": ["advisor_review"],
                            "verifierRanAtUtc": "2026-06-21T10:12:00Z",
                            "actionPolicyVersion": "lotus-idea.ai-action-content-policy.v1",
                        },
                        "approvedMetadataKeys": ["channel"],
                        "aiLineageRecorded": True,
                        "aiLineagePersistenceDecision": "accepted",
                        "durableStorageBacked": False,
                        "lotusAiRuntimeExecuted": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **merged_problem_response_metadata(
            status_code=status.HTTP_400_BAD_REQUEST,
            description="AI explanation request validation failed.",
            responses=(
                invalid_request_metadata(
                    detail=(
                        "Correct the AI explanation evaluation request or Idempotency-Key "
                        "and retry."
                    ),
                ),
                problem_response_metadata(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="invalid_ai_workflow_pack",
                    title="Invalid AI workflow pack",
                    detail=("Use the registered Lotus AI idea explanation workflow pack contract."),
                    description="Workflow pack identity is not registered for idea explanations.",
                ),
                problem_response_metadata(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="invalid_ai_output",
                    title="Invalid AI output",
                    detail=(
                        "The AI workflow output does not match the governed explanation request."
                    ),
                    description="AI workflow output did not match the governed request.",
                ),
            ),
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to evaluate idea AI explanations.",
            description="Caller lacks AI explanation permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="No idea candidate exists for the requested candidateId.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="idempotency_conflict",
            title="AI explanation request conflict",
            detail=(
                "The requested AI explanation conflicts with the candidate state, "
                "existing request lineage, or Idempotency-Key fingerprint."
            ),
            description="AI explanation evaluation request conflicts with governed state.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_ai_governance_routes(app: FastAPI) -> None:
    app.get(
        path=AI_EXPLANATION_READINESS_ROUTE["path"],
        operation_id=AI_EXPLANATION_READINESS_ROUTE["operation_id"],
        summary=AI_EXPLANATION_READINESS_ROUTE["summary"],
        description=AI_EXPLANATION_READINESS_ROUTE["description"],
        status_code=AI_EXPLANATION_READINESS_ROUTE["status_code"],
        response_model=AI_EXPLANATION_READINESS_ROUTE["response_model"],
        tags=AI_EXPLANATION_READINESS_ROUTE["tags"],
        responses=AI_EXPLANATION_READINESS_ROUTE["responses"],
    )(get_ai_explanation_readiness)
    app.post(
        path=AI_EXPLANATION_ROUTE["path"],
        operation_id=AI_EXPLANATION_ROUTE["operation_id"],
        summary=AI_EXPLANATION_ROUTE["summary"],
        description=AI_EXPLANATION_ROUTE["description"],
        status_code=AI_EXPLANATION_ROUTE["status_code"],
        response_model=AI_EXPLANATION_ROUTE["response_model"],
        tags=AI_EXPLANATION_ROUTE["tags"],
        responses=AI_EXPLANATION_ROUTE["responses"],
    )(evaluate_ai_explanation)


__all__ = [
    "AIExplanationEvaluationRequest",
    "AIExplanationEvaluationResponse",
    "AIExplanationReadinessResponse",
    "AIOutputClaimRequest",
    "AIProposedActionRequest",
    "AIWorkflowOutputRequest",
    "AIWorkflowOutputSummaryResponse",
    "AIWorkflowPackRequest",
    "AIWorkflowPackResponse",
    "RedactedIdeaEvidenceResponse",
    "RedactedSourceRefResponse",
    "evaluate_ai_explanation",
    "get_ai_explanation_readiness",
    "register_ai_governance_routes",
]
