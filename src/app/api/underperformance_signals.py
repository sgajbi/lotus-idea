from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_context_from_headers
from app.api.signal_models import (
    IdeaCandidateSummaryResponse,
    ReviewAccessScopeRequest,
    SourceRefRequest,
)
from app.api.signal_api_support import (
    RouteMetadata,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_refs,
)
from app.application.underperformance_signal import (
    EvaluateUnderperformanceSignalCommand,
    evaluate_underperformance_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


class EvaluateUnderperformanceSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Performance return evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_active_return: Decimal | None = Field(
        default=None,
        alias="sourceReportedActiveReturn",
        ge=Decimal("-1"),
        le=Decimal("1"),
        description=(
            "Active return reported by the Performance returns source. "
            "lotus-idea does not calculate returns or benchmark-relative performance."
        ),
        examples=["-0.0125"],
    )
    benchmark_context_available: bool = Field(
        ...,
        alias="benchmarkContextAvailable",
        description=(
            "Whether the caller's source-owned evidence includes enough benchmark context "
            "for advisor-review underperformance posture."
        ),
        examples=[True],
    )
    performance_ref: SourceRefRequest | None = Field(
        default=None,
        alias="performanceRef",
        description="Source-owned Lotus Performance returns evidence reference.",
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
        examples=["idea_underperformance_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must be timezone-aware")
        return value

    def to_command(self) -> EvaluateUnderperformanceSignalCommand:
        return EvaluateUnderperformanceSignalCommand(
            as_of_date=self.as_of_date,
            source_reported_active_return=self.source_reported_active_return,
            benchmark_context_available=self.benchmark_context_available,
            performance_ref=(
                self.performance_ref.to_domain() if self.performance_ref is not None else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateUnderperformanceSignalResponse(CamelModel):
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
    ) -> "EvaluateUnderperformanceSignalResponse":
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


async def evaluate_underperformance_signal(
    request: EvaluateUnderperformanceSignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateUnderperformanceSignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    source_authority = source_authority_from_refs((request.performance_ref,))
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    result = evaluate_underperformance_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateUnderperformanceSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


UNDERPERFORMANCE_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/underperformance/evaluate",
    "operation_id": "evaluateUnderperformanceIdeaSignal",
    "summary": "Evaluate an underperformance idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Lotus Performance active-return "
        "and benchmark-context evidence for underperformance review posture. The "
        "endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "calculate returns, assign benchmarks, certify benchmark methodology, "
        "recommend trades, create rebalance actions, publish client communication, "
        "certify a data product, prove Gateway/Workbench behavior, or promote a "
        "supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateUnderperformanceSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Underperformance signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "underperformance",
                        "reasonCodes": ["underperformance_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_underperformance_8d57adbf52f7f5a7",
                            "family": "underperformance",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_underperformance_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "74",
                            "scorePolicyVersion": "underperformance-review-v1",
                            "sourceSignalIds": ["signal_underperformance_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-performance:ReturnsSeriesBundle:v1",
                                    "sourceSystem": "lotus-performance",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "ready",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-performance",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


def register_underperformance_signal_routes(app: FastAPI) -> None:
    app.post(
        path=UNDERPERFORMANCE_EVALUATE_ROUTE["path"],
        operation_id=UNDERPERFORMANCE_EVALUATE_ROUTE["operation_id"],
        summary=UNDERPERFORMANCE_EVALUATE_ROUTE["summary"],
        description=UNDERPERFORMANCE_EVALUATE_ROUTE["description"],
        status_code=UNDERPERFORMANCE_EVALUATE_ROUTE["status_code"],
        response_model=UNDERPERFORMANCE_EVALUATE_ROUTE["response_model"],
        tags=UNDERPERFORMANCE_EVALUATE_ROUTE["tags"],
        responses=UNDERPERFORMANCE_EVALUATE_ROUTE["responses"],
    )(evaluate_underperformance_signal)
