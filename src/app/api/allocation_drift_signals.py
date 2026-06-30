from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.signal_models import (
    IdeaCandidateSummaryResponse,
    ReviewAccessScopeRequest,
    SourceRefRequest,
)
from app.api.temporal_validation import require_timezone_aware
from app.api.signal_api_support import (
    RouteMetadata,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_refs,
)
from app.application.mandate_health_signal import (
    EvaluateMandateHealthSignalCommand,
    evaluate_mandate_health_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


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


class EvaluateAllocationDriftSignalResponse(CamelModel):
    outcome: str
    family: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    candidate: IdeaCandidateSummaryResponse | None
    source_authority: str = Field(..., alias="sourceAuthority")
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description="False until live source, Gateway/Workbench, data-mesh, and supported-feature proof exists.",
    )

    @classmethod
    def from_domain(
        cls,
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> "EvaluateAllocationDriftSignalResponse":
        return cls(
            outcome=result.outcome.value,
            family=result.family.value,
            reasonCodes=tuple(reason.value for reason in result.reason_codes),
            unsupportedReasons=tuple(reason.value for reason in result.unsupported_reasons),
            candidate=(
                IdeaCandidateSummaryResponse.from_domain(result.candidate)
                if result.candidate is not None
                else None
            ),
            sourceAuthority=source_authority,
            supportedFeaturePromoted=False,
        )


async def evaluate_allocation_drift_signal(
    request: EvaluateAllocationDriftSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateAllocationDriftSignalResponse | JSONResponse:
    source_authority = source_authority_from_refs(
        (
            request.action_register_ref,
            request.mandate_performance_health_ref,
            request.mandate_risk_health_ref,
        )
    )
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
