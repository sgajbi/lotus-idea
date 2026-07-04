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
    SignalSourceRefContract,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    signal_source_ref_contract_problem_or_none,
    source_authority_from_contracts,
)
from app.application.high_volatility_signal import (
    EvaluateHighVolatilitySignalCommand,
    evaluate_high_volatility_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


class EvaluateHighVolatilitySignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Risk volatility evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_volatility: Decimal | None = Field(
        default=None,
        alias="sourceReportedVolatility",
        ge=Decimal("0"),
        description=(
            "Volatility reported by the Lotus Risk metrics source. lotus-idea does "
            "not calculate volatility, VaR, tracking error, or risk methodology."
        ),
        examples=["14.25"],
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
    risk_ref: SourceRefRequest | None = Field(
        default=None,
        alias="riskRef",
        description="Source-owned Lotus Risk metrics evidence reference.",
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
        examples=["idea_high_volatility_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateHighVolatilitySignalCommand:
        return EvaluateHighVolatilitySignalCommand(
            as_of_date=self.as_of_date,
            source_reported_volatility=self.source_reported_volatility,
            risk_supportability_state=self.risk_supportability_state,
            risk_ref=(self.risk_ref.to_domain() if self.risk_ref is not None else None),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateHighVolatilitySignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_high_volatility_signal(
    request: EvaluateHighVolatilitySignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateHighVolatilitySignalResponse | JSONResponse:
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

    result = evaluate_high_volatility_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateHighVolatilitySignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


def _source_ref_contracts(
    request: EvaluateHighVolatilitySignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.risk_ref,
            SourceSystem.LOTUS_RISK,
            ("lotus-risk:RiskMetricsReport:v1",),
        ),
    )


HIGH_VOLATILITY_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-volatility/evaluate",
    "operation_id": "evaluateHighVolatilityIdeaSignal",
    "summary": "Evaluate a high-volatility idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Lotus Risk metrics evidence for "
        "high-volatility review posture. The endpoint is a bounded API foundation; "
        "it does not fetch upstream sources, calculate volatility, approve Risk "
        "methodology, recommend trades, create rebalance actions, publish client "
        "communication, certify a data product, prove Gateway/Workbench behavior, "
        "or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateHighVolatilitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "High-volatility signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "high_volatility",
                        "reasonCodes": ["volatility_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_high_volatility_8d57adbf52f7f5a7",
                            "family": "high_volatility",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_volatility_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "72",
                            "scorePolicyVersion": "high-volatility-attention-v1",
                            "sourceSignalIds": ["signal_high_volatility_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-risk:RiskMetricsReport:v1",
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


def register_high_volatility_signal_routes(app: FastAPI) -> None:
    app.post(
        path=HIGH_VOLATILITY_EVALUATE_ROUTE["path"],
        operation_id=HIGH_VOLATILITY_EVALUATE_ROUTE["operation_id"],
        summary=HIGH_VOLATILITY_EVALUATE_ROUTE["summary"],
        description=HIGH_VOLATILITY_EVALUATE_ROUTE["description"],
        status_code=HIGH_VOLATILITY_EVALUATE_ROUTE["status_code"],
        response_model=HIGH_VOLATILITY_EVALUATE_ROUTE["response_model"],
        tags=HIGH_VOLATILITY_EVALUATE_ROUTE["tags"],
        responses=HIGH_VOLATILITY_EVALUATE_ROUTE["responses"],
    )(evaluate_high_volatility_signal)
