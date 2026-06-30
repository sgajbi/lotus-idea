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
from app.application.missing_risk_profile_signal import (
    EvaluateMissingRiskProfileSignalCommand,
    evaluate_missing_risk_profile_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


class EvaluateMissingRiskProfileSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned risk-profile posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    risk_profile_ref: SourceRefRequest | None = Field(
        default=None,
        alias="riskProfileRef",
        description="Source-owned Advise risk-profile or policy-evaluation posture reference.",
    )
    risk_profile_status: str | None = Field(
        default=None,
        alias="riskProfileStatus",
        description="Source-owned risk-profile posture such as MISSING, STALE, EXPIRED, REVIEW_DUE, or CURRENT.",
        examples=["STALE"],
    )
    risk_profile_effective_for_as_of_date: bool | None = Field(
        default=None,
        alias="riskProfileEffectiveForAsOfDate",
        description="Whether the source reports the risk profile is effective for the business date.",
    )
    risk_profile_review_due: bool | None = Field(
        default=None,
        alias="riskProfileReviewDue",
        description="Whether the source reports a risk-profile review is due.",
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
        examples=["idea_missing_risk_profile_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateMissingRiskProfileSignalCommand:
        return EvaluateMissingRiskProfileSignalCommand(
            as_of_date=self.as_of_date,
            risk_profile_ref=(
                self.risk_profile_ref.to_domain() if self.risk_profile_ref is not None else None
            ),
            risk_profile_status=self.risk_profile_status,
            risk_profile_effective_for_as_of_date=self.risk_profile_effective_for_as_of_date,
            risk_profile_review_due=self.risk_profile_review_due,
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateMissingRiskProfileSignalResponse(CamelModel):
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
    ) -> "EvaluateMissingRiskProfileSignalResponse":
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


async def evaluate_missing_risk_profile_signal(
    request: EvaluateMissingRiskProfileSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingRiskProfileSignalResponse | JSONResponse:
    source_authority = source_authority_from_refs((request.risk_profile_ref,))
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

    result = evaluate_missing_risk_profile_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateMissingRiskProfileSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


MISSING_RISK_PROFILE_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-risk-profile/evaluate",
    "operation_id": "evaluateMissingRiskProfileIdeaSignal",
    "summary": "Evaluate a missing risk-profile idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Advise evidence for missing, stale, "
        "expired, or review-due risk-profile posture. The endpoint is a bounded API "
        "foundation; it does not fetch upstream sources, approve risk profiling, approve "
        "suitability, approve policy, publish client communication, certify a typed "
        "risk-profile data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingRiskProfileSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Missing risk-profile signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "missing_risk_profile",
                        "reasonCodes": ["missing_risk_profile", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_missing_risk_profile_8d57adbf52f7f5a7",
                            "family": "missing_risk_profile",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_missing_risk_profile_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "64",
                            "scorePolicyVersion": "missing-risk-profile-review-v1",
                            "sourceSignalIds": ["signal_missing_risk_profile_8d57adbf52f7f5a7"],
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


def register_missing_risk_profile_signal_routes(app: FastAPI) -> None:
    app.post(
        path=MISSING_RISK_PROFILE_EVALUATE_ROUTE["path"],
        operation_id=MISSING_RISK_PROFILE_EVALUATE_ROUTE["operation_id"],
        summary=MISSING_RISK_PROFILE_EVALUATE_ROUTE["summary"],
        description=MISSING_RISK_PROFILE_EVALUATE_ROUTE["description"],
        status_code=MISSING_RISK_PROFILE_EVALUATE_ROUTE["status_code"],
        response_model=MISSING_RISK_PROFILE_EVALUATE_ROUTE["response_model"],
        tags=MISSING_RISK_PROFILE_EVALUATE_ROUTE["tags"],
        responses=MISSING_RISK_PROFILE_EVALUATE_ROUTE["responses"],
    )(evaluate_missing_risk_profile_signal)
