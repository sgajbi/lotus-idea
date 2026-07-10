from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import (
    problem_details_response as problem_response,
    service_unavailable_metadata,
)
from app.api.runtime_dependencies import PerformanceUnderperformanceSourceRuntimeBlocker
from app.api.runtime_dependencies import (
    build_performance_underperformance_source_runtime_from_environment as _build_performance_underperformance_source_runtime_from_environment,
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
    close_signal_source_runtime,
    evaluate_caller_supplied_signal,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_contracts,
)
from app.application.access_scope import portfolio_only_scope
from app.application.underperformance_signal import (
    EvaluateUnderperformanceFromPerformanceCommand,
    EvaluateUnderperformanceSignalCommand,
    evaluate_underperformance_signal_from_performance,
    evaluate_underperformance_signal_command,
)
from app.domain import SourceSystem
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


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
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

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


class EvaluateUnderperformanceFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Lotus Performance returns evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Lotus Performance returns-series evidence.",
        examples=["2026-06-21"],
    )
    period_name: str = Field(
        ...,
        alias="periodName",
        min_length=1,
        description=(
            "Canonical Lotus Performance period name used when requesting "
            "source-owned returns-series evidence. lotus-idea forwards the "
            "period and does not calculate returns, assign benchmarks, or "
            "approve benchmark methodology."
        ),
        examples=["YTD"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    reporting_currency: str | None = Field(
        default=None,
        alias="reportingCurrency",
        min_length=3,
        max_length=3,
        description="Optional ISO currency code forwarded to Lotus Performance.",
        examples=["USD"],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_underperformance_existing"],
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

    @field_validator("reporting_currency")
    @classmethod
    def _reporting_currency_must_be_normalized(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("reportingCurrency must be a 3-letter ISO currency code")
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
    ) -> EvaluateUnderperformanceFromPerformanceCommand:
        return EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            period_name=self.period_name,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            reporting_currency=self.reporting_currency,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateUnderperformanceSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_underperformance_signal(
    request: EvaluateUnderperformanceSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateUnderperformanceSignalResponse | JSONResponse:
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
        evaluator=evaluate_underperformance_signal_command,
        response_factory=EvaluateUnderperformanceSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_underperformance_signal_from_source(
    request: Request,
    signal_request: EvaluateUnderperformanceFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateUnderperformanceSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_PERFORMANCE.value
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    runtime = _build_performance_underperformance_source_runtime_from_environment()
    if isinstance(runtime, PerformanceUnderperformanceSourceRuntimeBlocker):
        emit_foundation_operation_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.BLOCKED,
            source_authority=source_authority,
            error_code=runtime.code,
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail=(
                "Performance source runtime is not configured for "
                "underperformance source evaluation."
            ),
        )

    try:
        result = evaluate_underperformance_signal_from_performance(
            signal_request.to_command(
                correlation_id=_request_correlation_id(request),
                trace_id=_request_trace_id(request),
            ),
            performance_source=runtime.performance_source,
        )
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )
        return EvaluateUnderperformanceSignalResponse.from_domain(
            result,
            source_authority=source_authority,
        )
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=SourceSystem.LOTUS_PERFORMANCE.value,
            emit_event=emit_foundation_operation_event,
        )


def _source_ref_contracts(
    request: EvaluateUnderperformanceSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.performance_ref,
            SourceSystem.LOTUS_PERFORMANCE,
            ("lotus-performance:ReturnsSeriesBundle:v1",),
        ),
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


UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/underperformance/evaluate-from-source",
    "operation_id": "evaluateUnderperformanceIdeaSignalFromSource",
    "summary": "Evaluate an underperformance idea signal from Lotus Performance",
    "description": (
        "Fetches source-owned Lotus Performance ReturnsSeriesBundle evidence "
        "through the configured Performance source adapter, then evaluates "
        "deterministic underperformance review posture. The endpoint does not "
        "persist candidates, calculate returns, assign benchmarks, approve "
        "benchmark methodology, recommend trades, create rebalance actions, "
        "certify live source support, create Gateway/Workbench support, publish "
        "client communication, certify a data product, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateUnderperformanceSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: UNDERPERFORMANCE_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail=(
                "Performance source runtime is not configured for "
                "underperformance source evaluation."
            ),
            description="Performance source runtime configuration is missing or invalid.",
        ),
    },
}


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


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
    app.post(
        path=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_underperformance_signal_from_source)
