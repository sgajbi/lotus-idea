from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

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
from app.application.drawdown_review_signal import (
    EvaluateDrawdownReviewSignalCommand,
    evaluate_drawdown_review_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


class EvaluateDrawdownReviewSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Risk drawdown evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_max_drawdown: Decimal | None = Field(
        default=None,
        alias="sourceReportedMaxDrawdown",
        ge=Decimal("-1"),
        le=Decimal("0"),
        description=(
            "Maximum drawdown reported by the Lotus Risk drawdown analytics source. "
            "lotus-idea does not calculate drawdown or approve risk methodology."
        ),
        examples=["-0.1245"],
    )
    risk_supportability_state: str | None = Field(
        default=None,
        alias="riskSupportabilityState",
        description=(
            "Source-owned Risk supportability posture. The current foundation accepts "
            "`ready` before creating a review candidate."
        ),
        examples=["ready"],
    )
    drawdown_ref: SourceRefRequest | None = Field(
        default=None,
        alias="drawdownRef",
        description="Source-owned Lotus Risk drawdown analytics evidence reference.",
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
        examples=["idea_drawdown_review_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateDrawdownReviewSignalCommand:
        return EvaluateDrawdownReviewSignalCommand(
            as_of_date=self.as_of_date,
            source_reported_max_drawdown=self.source_reported_max_drawdown,
            risk_supportability_state=self.risk_supportability_state,
            risk_ref=(self.drawdown_ref.to_domain() if self.drawdown_ref is not None else None),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateDrawdownReviewSignalResponse(CamelModel):
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
    ) -> "EvaluateDrawdownReviewSignalResponse":
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


async def evaluate_drawdown_review_signal(
    request: EvaluateDrawdownReviewSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateDrawdownReviewSignalResponse | JSONResponse:
    source_authority = source_authority_from_refs((request.drawdown_ref,))
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

    result = evaluate_drawdown_review_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateDrawdownReviewSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


DRAWDOWN_REVIEW_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/drawdown-review/evaluate",
    "operation_id": "evaluateDrawdownReviewIdeaSignal",
    "summary": "Evaluate a drawdown review idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Lotus Risk drawdown analytics "
        "evidence for high-volatility / drawdown review posture. The endpoint is "
        "a bounded API foundation; it does not fetch upstream sources, calculate "
        "drawdown, approve risk methodology, recommend trades, create rebalance "
        "actions, publish client communication, certify a data product, prove "
        "Gateway/Workbench behavior, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateDrawdownReviewSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Drawdown review signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "high_volatility",
                        "reasonCodes": ["drawdown_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_drawdown_review_8d57adbf52f7f5a7",
                            "family": "high_volatility",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_drawdown_review_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "72",
                            "scorePolicyVersion": "drawdown-review-attention-v1",
                            "sourceSignalIds": ["signal_drawdown_review_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-risk:DrawdownAnalyticsReport:v1",
                                    "sourceSystem": "lotus-risk",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "ready",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-risk",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


def register_drawdown_review_signal_routes(app: FastAPI) -> None:
    app.post(
        path=DRAWDOWN_REVIEW_EVALUATE_ROUTE["path"],
        operation_id=DRAWDOWN_REVIEW_EVALUATE_ROUTE["operation_id"],
        summary=DRAWDOWN_REVIEW_EVALUATE_ROUTE["summary"],
        description=DRAWDOWN_REVIEW_EVALUATE_ROUTE["description"],
        status_code=DRAWDOWN_REVIEW_EVALUATE_ROUTE["status_code"],
        response_model=DRAWDOWN_REVIEW_EVALUATE_ROUTE["response_model"],
        tags=DRAWDOWN_REVIEW_EVALUATE_ROUTE["tags"],
        responses=DRAWDOWN_REVIEW_EVALUATE_ROUTE["responses"],
    )(evaluate_drawdown_review_signal)
