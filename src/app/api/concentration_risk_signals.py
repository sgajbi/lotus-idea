from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.signal_models import (
    ReviewAccessScopeRequest,
    SignalEvaluationResponse,
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
from app.application.concentration_risk_signal import (
    EvaluateConcentrationRiskSignalCommand,
    evaluate_concentration_risk_signal_command,
)
from app.observability import emit_foundation_operation_event


class EvaluateConcentrationRiskSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Risk concentration evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    top_position_weight_current: Decimal | None = Field(
        default=None,
        alias="topPositionWeightCurrent",
        ge=Decimal("0"),
        le=Decimal("1"),
        description=(
            "Top single-position weight reported by the Risk concentration source. "
            "lotus-idea does not calculate concentration weights."
        ),
        examples=["0.18"],
    )
    top_issuer_weight_current: Decimal | None = Field(
        default=None,
        alias="topIssuerWeightCurrent",
        ge=Decimal("0"),
        le=Decimal("1"),
        description=(
            "Top issuer or counterparty weight reported by the Risk concentration "
            "source. lotus-idea does not calculate issuer exposure."
        ),
        examples=["0.24"],
    )
    issuer_coverage_status: str | None = Field(
        default=None,
        alias="issuerCoverageStatus",
        description=(
            "Source-owned issuer coverage posture. The current foundation accepts "
            "`complete` before creating a review candidate."
        ),
        examples=["complete"],
    )
    concentration_ref: SourceRefRequest | None = Field(
        default=None,
        alias="concentrationRef",
        description="Source-owned Lotus Risk concentration report reference.",
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
        examples=["idea_concentration_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateConcentrationRiskSignalCommand:
        return EvaluateConcentrationRiskSignalCommand(
            as_of_date=self.as_of_date,
            top_position_weight_current=self.top_position_weight_current,
            top_issuer_weight_current=self.top_issuer_weight_current,
            issuer_coverage_status=self.issuer_coverage_status,
            concentration_ref=(
                self.concentration_ref.to_domain() if self.concentration_ref is not None else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateConcentrationRiskSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_concentration_risk_signal(
    request: EvaluateConcentrationRiskSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateConcentrationRiskSignalResponse | JSONResponse:
    source_authority = source_authority_from_refs((request.concentration_ref,))
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

    result = evaluate_concentration_risk_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateConcentrationRiskSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


CONCENTRATION_RISK_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/concentration-risk/evaluate",
    "operation_id": "evaluateConcentrationRiskIdeaSignal",
    "summary": "Evaluate a concentration risk idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Lotus Risk concentration evidence "
        "for single-position or issuer concentration review posture. The endpoint "
        "is a bounded API foundation; it does not fetch upstream sources, calculate "
        "concentration, approve risk methodology, recommend trades, create rebalance "
        "actions, publish client communication, certify a data product, or promote a "
        "supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateConcentrationRiskSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Concentration signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "concentration",
                        "reasonCodes": ["concentration_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_concentration_8d57adbf52f7f5a7",
                            "family": "concentration",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_concentration_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "78",
                            "scorePolicyVersion": "concentration-attention-v1",
                            "sourceSignalIds": ["signal_concentration_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-risk:ConcentrationRiskReport:v1",
                                    "sourceSystem": "lotus-risk",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "quality_passed",
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


def register_concentration_risk_signal_routes(app: FastAPI) -> None:
    app.post(
        path=CONCENTRATION_RISK_EVALUATE_ROUTE["path"],
        operation_id=CONCENTRATION_RISK_EVALUATE_ROUTE["operation_id"],
        summary=CONCENTRATION_RISK_EVALUATE_ROUTE["summary"],
        description=CONCENTRATION_RISK_EVALUATE_ROUTE["description"],
        status_code=CONCENTRATION_RISK_EVALUATE_ROUTE["status_code"],
        response_model=CONCENTRATION_RISK_EVALUATE_ROUTE["response_model"],
        tags=CONCENTRATION_RISK_EVALUATE_ROUTE["tags"],
        responses=CONCENTRATION_RISK_EVALUATE_ROUTE["responses"],
    )(evaluate_concentration_risk_signal)
