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
from app.api.runtime_dependencies import RiskDrawdownSourceRuntimeBlocker
from app.api.runtime_dependencies import (
    build_risk_drawdown_source_runtime_from_environment as _build_risk_drawdown_source_runtime_from_environment,
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
from app.application.drawdown_review_signal import (
    EvaluateDrawdownReviewFromRiskCommand,
    EvaluateDrawdownReviewSignalCommand,
    evaluate_drawdown_review_signal_from_risk,
    evaluate_drawdown_review_signal_command,
)
from app.domain import SourceSystem
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


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


class EvaluateDrawdownReviewFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Lotus Risk drawdown analytics.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Lotus Risk drawdown analytics evidence.",
        examples=["2026-06-21"],
    )
    period_name: str = Field(
        ...,
        alias="periodName",
        min_length=1,
        description=(
            "Canonical Lotus Risk period name used when requesting source-owned "
            "drawdown analytics. lotus-idea forwards the period and does not "
            "calculate drawdown or approve risk methodology."
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
        examples=["idea_drawdown_review_existing"],
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
    ) -> EvaluateDrawdownReviewFromRiskCommand:
        return EvaluateDrawdownReviewFromRiskCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            period_name=self.period_name,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateDrawdownReviewSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_drawdown_review_signal(
    request: EvaluateDrawdownReviewSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateDrawdownReviewSignalResponse | JSONResponse:
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
        evaluator=evaluate_drawdown_review_signal_command,
        response_factory=EvaluateDrawdownReviewSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_drawdown_review_signal_from_source(
    request: Request,
    signal_request: EvaluateDrawdownReviewFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateDrawdownReviewSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_RISK.value
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    runtime = _build_risk_drawdown_source_runtime_from_environment()
    if isinstance(runtime, RiskDrawdownSourceRuntimeBlocker):
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
            detail="Risk source runtime is not configured for drawdown-review source evaluation.",
        )

    try:
        result = evaluate_drawdown_review_signal_from_risk(
            signal_request.to_command(
                correlation_id=_request_correlation_id(request),
                trace_id=_request_trace_id(request),
            ),
            risk_source=runtime.risk_source,
        )
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )
        return EvaluateDrawdownReviewSignalResponse.from_domain(
            result,
            source_authority=source_authority,
        )
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=SourceSystem.LOTUS_RISK.value,
            emit_event=emit_foundation_operation_event,
        )


def _source_ref_contracts(
    request: EvaluateDrawdownReviewSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.drawdown_ref,
            SourceSystem.LOTUS_RISK,
            ("lotus-risk:DrawdownAnalyticsReport:v1",),
        ),
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


DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/drawdown-review/evaluate-from-source",
    "operation_id": "evaluateDrawdownReviewIdeaSignalFromSource",
    "summary": "Evaluate a drawdown review idea signal from Lotus Risk",
    "description": (
        "Fetches source-owned Lotus Risk DrawdownAnalyticsReport evidence through "
        "the configured Risk source adapter, then evaluates deterministic "
        "drawdown-review posture. The endpoint does not persist candidates, "
        "calculate drawdown, approve risk methodology, recommend trades, create "
        "rebalance actions, certify live source support, create Gateway/Workbench "
        "support, publish client communication, certify a data product, or promote "
        "a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateDrawdownReviewSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: DRAWDOWN_REVIEW_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Risk source runtime is not configured for drawdown-review source evaluation.",
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
    app.post(
        path=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_drawdown_review_signal_from_source)
