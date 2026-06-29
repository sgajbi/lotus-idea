from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.idea_signals import (
    CamelModel,
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
from app.application.bond_maturity_signal import (
    EvaluateBondMaturitySignalCommand,
    evaluate_bond_maturity_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


class EvaluateBondMaturitySignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Core maturity evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_next_maturity_date: date | None = Field(
        default=None,
        alias="sourceReportedNextMaturityDate",
        description=(
            "Next maturity date reported by the Core holdings source. lotus-idea "
            "does not calculate maturity schedules or replacement recommendations."
        ),
        examples=["2026-07-10"],
    )
    source_reported_maturing_position_count: int | None = Field(
        default=None,
        alias="sourceReportedMaturingPositionCount",
        ge=0,
        description="Number of maturing positions reported by the Core holdings source.",
        examples=[2],
    )
    holdings_ref: SourceRefRequest | None = Field(
        default=None,
        alias="holdingsRef",
        description="Source-owned Core holdings reference.",
    )
    maturity_fact_ref: SourceRefRequest | None = Field(
        default=None,
        alias="maturityFactRef",
        description="Source-owned Core maturity-fact reference.",
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
        examples=["idea_bond_maturity_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must be timezone-aware")
        return value

    def to_command(self) -> EvaluateBondMaturitySignalCommand:
        return EvaluateBondMaturitySignalCommand(
            as_of_date=self.as_of_date,
            source_reported_next_maturity_date=self.source_reported_next_maturity_date,
            source_reported_maturing_position_count=self.source_reported_maturing_position_count,
            holdings_ref=(self.holdings_ref.to_domain() if self.holdings_ref is not None else None),
            maturity_fact_ref=(
                self.maturity_fact_ref.to_domain() if self.maturity_fact_ref is not None else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateBondMaturitySignalResponse(CamelModel):
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
    ) -> "EvaluateBondMaturitySignalResponse":
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


async def evaluate_bond_maturity_signal(
    request: EvaluateBondMaturitySignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateBondMaturitySignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    source_authority = source_authority_from_refs((request.holdings_ref, request.maturity_fact_ref))
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    result = evaluate_bond_maturity_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateBondMaturitySignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


BOND_MATURITY_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/bond-maturity/evaluate",
    "operation_id": "evaluateBondMaturityIdeaSignal",
    "summary": "Evaluate a bond maturity idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core holdings maturity evidence "
        "for bond-maturity / reinvestment review posture. The endpoint is a "
        "bounded API foundation; it does not fetch upstream sources, recommend "
        "replacement products, calculate reinvestment advice, approve planning "
        "suitability, create orders, publish client communication, certify a data "
        "product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateBondMaturitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Bond maturity signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "bond_maturity",
                        "reasonCodes": ["maturity_window", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_bond_maturity_8d57adbf52f7f5a7",
                            "family": "bond_maturity",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_bond_maturity_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "70",
                            "scorePolicyVersion": "bond-maturity-review-v1",
                            "sourceSignalIds": ["signal_bond_maturity_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:HoldingsAsOf:v1",
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


def register_bond_maturity_signal_routes(app: FastAPI) -> None:
    app.post(
        path=BOND_MATURITY_EVALUATE_ROUTE["path"],
        operation_id=BOND_MATURITY_EVALUATE_ROUTE["operation_id"],
        summary=BOND_MATURITY_EVALUATE_ROUTE["summary"],
        description=BOND_MATURITY_EVALUATE_ROUTE["description"],
        status_code=BOND_MATURITY_EVALUATE_ROUTE["status_code"],
        response_model=BOND_MATURITY_EVALUATE_ROUTE["response_model"],
        tags=BOND_MATURITY_EVALUATE_ROUTE["tags"],
        responses=BOND_MATURITY_EVALUATE_ROUTE["responses"],
    )(evaluate_bond_maturity_signal)
