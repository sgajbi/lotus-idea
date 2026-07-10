from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import service_unavailable_metadata
from app.api.runtime_dependencies import (
    RiskVolatilitySourceRuntime,
    RiskVolatilitySourceRuntimeBlocker,
)
from app.api.runtime_dependencies import (
    build_risk_volatility_source_runtime_from_environment as _build_risk_volatility_source_runtime_from_environment,
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
    evaluate_caller_supplied_signal,
    evaluate_source_signal,
    signal_problem_responses,
    source_authority_from_contracts,
)
from app.application.access_scope import portfolio_only_scope
from app.application.high_volatility_signal import (
    EvaluateHighVolatilityFromRiskCommand,
    EvaluateHighVolatilitySignalCommand,
    evaluate_high_volatility_signal_from_risk,
    evaluate_high_volatility_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


def _is_risk_volatility_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, RiskVolatilitySourceRuntimeBlocker)


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


class EvaluateHighVolatilityFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Lotus Risk metrics evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Lotus Risk metrics evidence.",
        examples=["2026-06-21"],
    )
    period_name: str = Field(
        ...,
        alias="periodName",
        min_length=1,
        description=(
            "Canonical Lotus Risk period name used when requesting source-owned "
            "volatility metrics. lotus-idea forwards the period and does not "
            "calculate volatility, VaR, or tracking error."
        ),
        examples=["YTD"],
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
        examples=["idea_high_volatility_existing"],
    )

    @field_validator("portfolio_id")
    @classmethod
    def _portfolio_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("portfolioId is required")
        return cleaned

    @field_validator("period_name")
    @classmethod
    def _period_name_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("periodName is required")
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
    ) -> EvaluateHighVolatilityFromRiskCommand:
        return EvaluateHighVolatilityFromRiskCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            period_name=self.period_name,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateHighVolatilitySignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_high_volatility_signal(
    request: EvaluateHighVolatilitySignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateHighVolatilitySignalResponse | JSONResponse:
    source_contracts = _source_ref_contracts(request)
    source_authority = source_authority_from_contracts(source_contracts)
    return evaluate_caller_supplied_signal(
        caller=caller,
        source_authority=source_authority,
        source_contracts=source_contracts,
        requested_access_scope=(
            request.access_scope.to_domain() if request.access_scope is not None else None
        ),
        command_factory=request.to_command,
        evaluator=evaluate_high_volatility_signal_command,
        response_factory=EvaluateHighVolatilitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_high_volatility_signal_from_source(
    request: Request,
    signal_request: EvaluateHighVolatilityFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateHighVolatilitySignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_RISK.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        runtime_factory=_build_risk_volatility_source_runtime_from_environment,
        is_runtime_blocked=_is_risk_volatility_runtime_blocked,
        blocked_detail="Risk source runtime is not configured for high-volatility source evaluation.",
        command_factory=lambda runtime, _tenant_id: signal_request.to_command(
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_high_volatility_signal_from_risk(
            command,
            risk_source=cast(RiskVolatilitySourceRuntime, runtime).risk_source,
        ),
        response_factory=EvaluateHighVolatilitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
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


HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-volatility/evaluate-from-source",
    "operation_id": "evaluateHighVolatilityIdeaSignalFromSource",
    "summary": "Evaluate a high-volatility idea signal from Lotus Risk",
    "description": (
        "Fetches source-owned Lotus Risk RiskMetricsReport volatility evidence "
        "through the configured Risk source adapter, then evaluates deterministic "
        "high-volatility review posture. The endpoint does not persist candidates, "
        "calculate volatility, approve risk methodology, recommend trades, create "
        "rebalance actions, certify live source support, create Gateway/Workbench "
        "support, publish client communication, certify a data product, or promote "
        "a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateHighVolatilitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: HIGH_VOLATILITY_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Risk source runtime is not configured for high-volatility source evaluation.",
            description="Risk source runtime configuration is missing or invalid.",
        ),
    },
}


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


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
    app.post(
        path=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_high_volatility_signal_from_source)
