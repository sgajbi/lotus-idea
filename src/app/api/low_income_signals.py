from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.idea_signals import (
    CamelModel,
    IdeaCandidateSummaryResponse,
    ReviewAccessScopeRequest,
    SourceRefRequest,
)
from app.application.low_income_signal import (
    EvaluateLowIncomeSignalCommand,
    evaluate_low_income_signal_command,
)
from app.domain import SignalEvaluationResult
from app.errors import ProblemDetails, problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


_EVALUATE_LOW_INCOME_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.signal.evaluate",
    allowed_roles=("advisor",),
)


class EvaluateLowIncomeSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Core cashflow evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_min_projected_cumulative_cashflow: Decimal | None = Field(
        default=None,
        alias="sourceReportedMinProjectedCumulativeCashflow",
        description=(
            "Minimum projected cumulative cashflow reported by the Core cashflow "
            "projection source. lotus-idea does not infer income needs or calculate "
            "planning suitability."
        ),
        examples=["-12500"],
    )
    cash_movement_count: int | None = Field(
        default=None,
        alias="cashMovementCount",
        ge=0,
        description="Number of cash movements reported by the Core cash movement source.",
        examples=[4],
    )
    cash_movement_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashMovementRef",
        description="Source-owned Core cash movement summary reference.",
    )
    cashflow_projection_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashflowProjectionRef",
        description="Source-owned Core cashflow projection reference.",
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
        examples=["idea_low_income_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must be timezone-aware")
        return value

    def to_command(self) -> EvaluateLowIncomeSignalCommand:
        return EvaluateLowIncomeSignalCommand(
            as_of_date=self.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                self.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=self.cash_movement_count,
            cash_movement_ref=(
                self.cash_movement_ref.to_domain() if self.cash_movement_ref is not None else None
            ),
            cashflow_projection_ref=(
                self.cashflow_projection_ref.to_domain()
                if self.cashflow_projection_ref is not None
                else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateLowIncomeSignalResponse(CamelModel):
    outcome: str
    family: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    candidate: IdeaCandidateSummaryResponse | None
    source_authority: str = Field(..., alias="sourceAuthority")
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description="False until live source adapters, Gateway/Workbench proof, and supported-feature registration exist.",
    )

    @classmethod
    def from_domain(
        cls,
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> "EvaluateLowIncomeSignalResponse":
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


async def evaluate_low_income_signal(
    request: EvaluateLowIncomeSignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateLowIncomeSignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    source_authority = _cashflow_source_authority(request)
    try:
        require_capability(caller, _EVALUATE_LOW_INCOME_POLICY)
    except PermissionDeniedError:
        emit_foundation_operation_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.PERMISSION_DENIED,
            source_authority=source_authority,
            error_code="permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea signals.",
        )

    result = evaluate_low_income_signal_command(request.to_command())
    emit_foundation_operation_event(
        IdeaOperation.SIGNAL_EVALUATION,
        _operation_outcome_from_signal_evaluation(result),
        source_authority=source_authority,
    )
    return EvaluateLowIncomeSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


def _operation_outcome_from_signal_evaluation(
    result: SignalEvaluationResult,
) -> OperationOutcome:
    outcome = result.outcome.value
    if outcome == "candidate_created":
        return OperationOutcome.ACCEPTED
    if outcome == "suppressed":
        return OperationOutcome.SUPPRESSED
    if outcome == "not_eligible":
        return OperationOutcome.NOT_ELIGIBLE
    return OperationOutcome.BLOCKED


def _cashflow_source_authority(request: EvaluateLowIncomeSignalRequest) -> str:
    source_systems = {
        source_ref.source_system.value
        for source_ref in (request.cash_movement_ref, request.cashflow_projection_ref)
        if source_ref is not None
    }
    if len(source_systems) == 1:
        return next(iter(source_systems))
    return "source-owned"


LOW_INCOME_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/low-income/evaluate",
    "operation_id": "evaluateLowIncomeIdeaSignal",
    "summary": "Evaluate a low-income liquidity shortfall idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core cashflow projection and cash "
        "movement evidence for low-income / liquidity-shortfall review posture. The "
        "endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "infer client income needs, provide funding advice, issue treasury "
        "instructions, approve planning suitability, publish client communication, "
        "certify a data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateLowIncomeSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Low-income signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "low_income",
                        "reasonCodes": ["income_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_low_income_8d57adbf52f7f5a7",
                            "family": "low_income",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_low_income_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "cashflow-liquidity-review-v1",
                            "sourceSignalIds": ["signal_low_income_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioCashflowProjection:v1",
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
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks the required signal-evaluation capability.",
        },
    },
}


def register_low_income_signal_routes(app: FastAPI) -> None:
    app.post(
        path=LOW_INCOME_EVALUATE_ROUTE["path"],
        operation_id=LOW_INCOME_EVALUATE_ROUTE["operation_id"],
        summary=LOW_INCOME_EVALUATE_ROUTE["summary"],
        description=LOW_INCOME_EVALUATE_ROUTE["description"],
        status_code=LOW_INCOME_EVALUATE_ROUTE["status_code"],
        response_model=LOW_INCOME_EVALUATE_ROUTE["response_model"],
        tags=LOW_INCOME_EVALUATE_ROUTE["tags"],
        responses=LOW_INCOME_EVALUATE_ROUTE["responses"],
    )(evaluate_low_income_signal)
