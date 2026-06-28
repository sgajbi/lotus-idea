from __future__ import annotations

from datetime import date, datetime
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
from app.application.bond_maturity_signal import (
    EvaluateBondMaturitySignalCommand,
    evaluate_bond_maturity_signal_command,
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


_EVALUATE_BOND_MATURITY_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.signal.evaluate",
    allowed_roles=("advisor",),
)


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
    source_authority = _maturity_source_authority(request)
    try:
        require_capability(caller, _EVALUATE_BOND_MATURITY_POLICY)
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

    result = evaluate_bond_maturity_signal_command(request.to_command())
    emit_foundation_operation_event(
        IdeaOperation.SIGNAL_EVALUATION,
        _operation_outcome_from_signal_evaluation(result),
        source_authority=source_authority,
    )
    return EvaluateBondMaturitySignalResponse.from_domain(
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


def _maturity_source_authority(request: EvaluateBondMaturitySignalRequest) -> str:
    source_systems = {
        source_ref.source_system.value
        for source_ref in (request.holdings_ref, request.maturity_fact_ref)
        if source_ref is not None
    }
    if len(source_systems) == 1:
        return next(iter(source_systems))
    return "source-owned"


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
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks the required signal-evaluation capability.",
        },
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
