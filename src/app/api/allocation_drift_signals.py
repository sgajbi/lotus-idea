from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import (
    problem_details_response as problem_response,
    service_unavailable_metadata,
)
from app.api.runtime_dependencies import ManageMandateHealthSourceRuntimeBlocker
from app.api.runtime_dependencies import (
    build_manage_mandate_health_source_runtime_from_environment as _build_manage_mandate_health_source_runtime_from_environment,
)
from app.api.signal_models import (
    ReviewAccessScopeRequest,
    SignalEvaluationResponse,
    SourceRefRequest,
)
from app.api.temporal_validation import require_timezone_aware
from app.api.signal_api_support import (
    RouteMetadata,
    SignalSourceRefContract,
    close_signal_source_runtime,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    signal_source_ref_contract_problem_or_none,
    source_authority_from_contracts,
)
from app.application.access_scope import portfolio_only_scope
from app.application.mandate_health_signal import (
    EvaluateMandateHealthFromManageCommand,
    EvaluateMandateHealthSignalCommand,
    evaluate_mandate_health_signal_from_manage,
    evaluate_mandate_health_signal_command,
)
from app.domain import SourceSystem
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


class EvaluateAllocationDriftSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned mandate and actionability evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    workflow_decision_count: int | None = Field(
        default=None,
        alias="workflowDecisionCount",
        ge=0,
        description="Workflow decision count reported by the source-owned Manage action register.",
        examples=[2],
    )
    lineage_edge_count: int | None = Field(
        default=None,
        alias="lineageEdgeCount",
        ge=0,
        description="Lineage edge count reported by the source-owned Manage action register.",
        examples=[4],
    )
    manage_supportability_state: str | None = Field(
        default=None,
        alias="manageSupportabilityState",
        description=(
            "Source-owned Manage supportability posture. The current foundation accepts "
            "`ready` before creating a PM-review candidate."
        ),
        examples=["ready"],
    )
    portfolio_scope_confirmed: bool = Field(
        ...,
        alias="portfolioScopeConfirmed",
        description=(
            "Whether the source-owned evidence is confirmed to be portfolio-scoped. "
            "Store-wide Manage posture blocks candidate creation."
        ),
        examples=[True],
    )
    action_register_ref: SourceRefRequest | None = Field(
        default=None,
        alias="actionRegisterRef",
        description="Source-owned Lotus Manage portfolio action-register evidence reference.",
    )
    mandate_performance_health_ref: SourceRefRequest | None = Field(
        default=None,
        alias="mandatePerformanceHealthRef",
        description="Optional source-owned Lotus Performance mandate health evidence reference.",
    )
    mandate_risk_health_ref: SourceRefRequest | None = Field(
        default=None,
        alias="mandateRiskHealthRef",
        description="Optional source-owned Lotus Risk mandate health evidence reference.",
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description="Optional review access scope carried onto created candidates.",
    )
    entitlement_allowed: bool = Field(
        default=True,
        alias="entitlementAllowed",
        description="Whether upstream caller/source entitlement already allowed this evidence for evaluation.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_allocation_drift_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateMandateHealthSignalCommand:
        return EvaluateMandateHealthSignalCommand(
            as_of_date=self.as_of_date,
            workflow_decision_count=self.workflow_decision_count,
            lineage_edge_count=self.lineage_edge_count,
            manage_supportability_state=self.manage_supportability_state,
            portfolio_scope_confirmed=self.portfolio_scope_confirmed,
            action_register_ref=(
                self.action_register_ref.to_domain()
                if self.action_register_ref is not None
                else None
            ),
            mandate_performance_health_ref=(
                self.mandate_performance_health_ref.to_domain()
                if self.mandate_performance_health_ref is not None
                else None
            ),
            mandate_risk_health_ref=(
                self.mandate_risk_health_ref.to_domain()
                if self.mandate_risk_health_ref is not None
                else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateAllocationDriftFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Lotus Manage action-register posture.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Lotus Manage action-register posture evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_allocation_drift_existing"],
    )

    @field_validator("portfolio_id")
    @classmethod
    def _portfolio_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("portfolioId is required")
        return cleaned

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(
        self,
        *,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> EvaluateMandateHealthFromManageCommand:
        return EvaluateMandateHealthFromManageCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateAllocationDriftSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_allocation_drift_signal(
    request: EvaluateAllocationDriftSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateAllocationDriftSignalResponse | JSONResponse:
    source_contracts = _source_ref_contracts(request)
    source_authority = source_authority_from_contracts(source_contracts)
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=(
            request.access_scope.to_domain() if request.access_scope is not None else None
        ),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem
    contract_problem = signal_source_ref_contract_problem_or_none(
        contracts=source_contracts,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if contract_problem is not None:
        return contract_problem

    result = evaluate_mandate_health_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateAllocationDriftSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


async def evaluate_allocation_drift_signal_from_source(
    request: Request,
    signal_request: EvaluateAllocationDriftFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateAllocationDriftSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_MANAGE.value
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    runtime = _build_manage_mandate_health_source_runtime_from_environment()
    if isinstance(runtime, ManageMandateHealthSourceRuntimeBlocker):
        emit_foundation_operation_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.BLOCKED,
            source_authority=source_authority,
            error_code=runtime.code,
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Manage source runtime is not configured for allocation-drift source evaluation.",
        )

    try:
        result = evaluate_mandate_health_signal_from_manage(
            signal_request.to_command(
                correlation_id=_request_correlation_id(request),
                trace_id=_request_trace_id(request),
            ),
            manage_source=runtime.manage_source,
        )
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )
        return EvaluateAllocationDriftSignalResponse.from_domain(
            result,
            source_authority=source_authority,
        )
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=SourceSystem.LOTUS_MANAGE.value,
            emit_event=emit_foundation_operation_event,
        )


def _source_ref_contracts(
    request: EvaluateAllocationDriftSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.action_register_ref,
            SourceSystem.LOTUS_MANAGE,
            ("lotus-manage:PortfolioActionRegister:v1",),
        ),
        SignalSourceRefContract(
            request.mandate_performance_health_ref,
            SourceSystem.LOTUS_PERFORMANCE,
            ("lotus-performance:MandatePerformanceHealthContext:v1",),
        ),
        SignalSourceRefContract(
            request.mandate_risk_health_ref,
            SourceSystem.LOTUS_RISK,
            ("lotus-risk:MandateRiskHealthContext:v1",),
        ),
    )


ALLOCATION_DRIFT_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/allocation-drift/evaluate",
    "operation_id": "evaluateAllocationDriftIdeaSignal",
    "summary": "Evaluate an allocation-drift idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Manage action-register and optional "
        "mandate health evidence for allocation-drift / mandate-review posture. The "
        "endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "calculate drift, approve mandate compliance, create rebalance actions, "
        "create orders, approve suitability, publish client communication, certify "
        "a data product, prove Gateway/Workbench behavior, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateAllocationDriftSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Allocation-drift signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "allocation_drift",
                        "reasonCodes": ["allocation_drift_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_allocation_drift_8d57adbf52f7f5a7",
                            "family": "allocation_drift",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "pm_review_required",
                            "evidencePacketId": "iep_allocation_drift_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "70",
                            "scorePolicyVersion": "allocation-drift-mandate-review-v1",
                            "sourceSignalIds": ["signal_allocation_drift_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-manage:PortfolioActionRegister:v1",
                                    "sourceSystem": "lotus-manage",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "ready",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-manage",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
    "operation_id": "evaluateAllocationDriftIdeaSignalFromSource",
    "summary": "Evaluate an allocation-drift idea signal from Lotus Manage",
    "description": (
        "Fetches source-owned Lotus Manage PortfolioActionRegister posture "
        "through the configured Manage source adapter, then evaluates "
        "deterministic allocation-drift / mandate-review posture. The endpoint "
        "does not persist candidates, calculate drift, approve mandate "
        "compliance, create rebalance actions, create orders, approve "
        "suitability, certify live source support, create Gateway/Workbench "
        "support, publish client communication, certify a data product, or "
        "promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateAllocationDriftSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: ALLOCATION_DRIFT_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Manage source runtime is not configured for allocation-drift source evaluation.",
            description="Manage source runtime configuration is missing or invalid.",
        ),
    },
}


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


def register_allocation_drift_signal_routes(app: FastAPI) -> None:
    app.post(
        path=ALLOCATION_DRIFT_EVALUATE_ROUTE["path"],
        operation_id=ALLOCATION_DRIFT_EVALUATE_ROUTE["operation_id"],
        summary=ALLOCATION_DRIFT_EVALUATE_ROUTE["summary"],
        description=ALLOCATION_DRIFT_EVALUATE_ROUTE["description"],
        status_code=ALLOCATION_DRIFT_EVALUATE_ROUTE["status_code"],
        response_model=ALLOCATION_DRIFT_EVALUATE_ROUTE["response_model"],
        tags=ALLOCATION_DRIFT_EVALUATE_ROUTE["tags"],
        responses=ALLOCATION_DRIFT_EVALUATE_ROUTE["responses"],
    )(evaluate_allocation_drift_signal)
    app.post(
        path=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_allocation_drift_signal_from_source)
