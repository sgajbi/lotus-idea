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
from app.api.runtime_dependencies import (
    CoreLowIncomeSourceRuntimeBlocker,
)
from app.api.runtime_dependencies import (
    build_core_low_income_source_runtime_from_environment as _build_core_low_income_source_runtime_from_environment,
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
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    signal_source_ref_contract_problem_or_none,
    source_authority_from_contracts,
)
from app.application.access_scope import portfolio_only_scope
from app.application.low_income_signal import (
    EvaluateLowIncomeFromCoreCommand,
    EvaluateLowIncomeSignalCommand,
    evaluate_low_income_signal_from_core,
    evaluate_low_income_signal_command,
)
from app.domain import SourceSystem
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


class EvaluateLowIncomeSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Core cashflow evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_min_projected_cumulative_cashflow: Decimal | None = Field(
        default=None,
        alias="sourceReportedMinProjectedCumulativeCashflow",
        description=(
            "Minimum projected cumulative cashflow reported by the Core cashflow "
            "projection source. lotus-idea does not infer income needs or calculate "
            "planning suitability."
        ),
        examples=["-12500"],
    )
    cash_movement_count: int | None = Field(
        default=None,
        alias="cashMovementCount",
        ge=0,
        description="Number of cash movements reported by the Core cash movement source.",
        examples=[4],
    )
    cash_movement_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashMovementRef",
        description="Source-owned Core cash movement summary reference.",
    )
    cashflow_projection_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashflowProjectionRef",
        description="Source-owned Core cashflow projection reference.",
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
        examples=["idea_low_income_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateLowIncomeSignalCommand:
        return EvaluateLowIncomeSignalCommand(
            as_of_date=self.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                self.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=self.cash_movement_count,
            cash_movement_ref=(
                self.cash_movement_ref.to_domain() if self.cash_movement_ref is not None else None
            ),
            cashflow_projection_ref=(
                self.cashflow_projection_ref.to_domain()
                if self.cashflow_projection_ref is not None
                else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateLowIncomeFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Core source products.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Core cashflow source evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    horizon_days: int = Field(
        default=30,
        alias="horizonDays",
        ge=1,
        le=366,
        description="Core cashflow projection horizon in days.",
        examples=[30],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_low_income_existing"],
    )

    @field_validator("portfolio_id")
    @classmethod
    def _portfolio_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("portfolioId is required")
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
    ) -> EvaluateLowIncomeFromCoreCommand:
        return EvaluateLowIncomeFromCoreCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            horizon_days=self.horizon_days,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateLowIncomeSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_low_income_signal(
    request: EvaluateLowIncomeSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateLowIncomeSignalResponse | JSONResponse:
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

    result = evaluate_low_income_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateLowIncomeSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


async def evaluate_low_income_signal_from_source(
    request: Request,
    signal_request: EvaluateLowIncomeFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateLowIncomeSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_CORE.value
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    runtime = _build_core_low_income_source_runtime_from_environment()
    if isinstance(runtime, CoreLowIncomeSourceRuntimeBlocker):
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
            detail=("Core source runtime is not configured for low-income source evaluation."),
        )

    try:
        result = evaluate_low_income_signal_from_core(
            signal_request.to_command(
                correlation_id=_request_correlation_id(request),
                trace_id=_request_trace_id(request),
            ),
            core_source=runtime.core_source,
        )
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )
        return EvaluateLowIncomeSignalResponse.from_domain(
            result,
            source_authority=source_authority,
        )
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=SourceSystem.LOTUS_CORE.value,
            emit_event=emit_foundation_operation_event,
        )


def _source_ref_contracts(
    request: EvaluateLowIncomeSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.cash_movement_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioCashMovementSummary:v1",),
        ),
        SignalSourceRefContract(
            request.cashflow_projection_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioCashflowProjection:v1",),
        ),
    )


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


LOW_INCOME_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/low-income/evaluate",
    "operation_id": "evaluateLowIncomeIdeaSignal",
    "summary": "Evaluate a low-income liquidity shortfall idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core cashflow projection and cash "
        "movement evidence for low-income / liquidity-shortfall review posture. The "
        "endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "infer client income needs, provide funding advice, issue treasury "
        "instructions, approve planning suitability, publish client communication, "
        "certify a data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateLowIncomeSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Low-income signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "low_income",
                        "reasonCodes": ["income_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_low_income_8d57adbf52f7f5a7",
                            "family": "low_income",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_low_income_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "cashflow-liquidity-review-v1",
                            "sourceSignalIds": ["signal_low_income_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioCashflowProjection:v1",
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


LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/low-income/evaluate-from-source",
    "operation_id": "evaluateLowIncomeIdeaSignalFromSource",
    "summary": "Evaluate a low-income liquidity shortfall idea signal from Core",
    "description": (
        "Fetches source-owned Core cash movement and cashflow projection evidence "
        "through the configured Core source adapter, then evaluates deterministic "
        "low-income / liquidity-shortfall candidate posture. The endpoint does not "
        "persist candidates, infer client income needs, provide funding advice, issue "
        "treasury instructions, approve planning suitability, certify live source "
        "support, create Gateway/Workbench support, or promote a supported business "
        "feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateLowIncomeSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Core-backed low-income signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "low_income",
                        "reasonCodes": ["income_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_low_income_8d57adbf52f7f5a7",
                            "family": "low_income",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_low_income_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "cashflow-liquidity-review-v1",
                            "sourceSignalIds": ["signal_low_income_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioCashflowProjection:v1",
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
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Core source runtime is not configured for low-income source evaluation.",
            description="Core source runtime configuration is missing or invalid.",
        ),
    },
}


def register_low_income_signal_routes(app: FastAPI) -> None:
    app.post(
        path=LOW_INCOME_EVALUATE_ROUTE["path"],
        operation_id=LOW_INCOME_EVALUATE_ROUTE["operation_id"],
        summary=LOW_INCOME_EVALUATE_ROUTE["summary"],
        description=LOW_INCOME_EVALUATE_ROUTE["description"],
        status_code=LOW_INCOME_EVALUATE_ROUTE["status_code"],
        response_model=LOW_INCOME_EVALUATE_ROUTE["response_model"],
        tags=LOW_INCOME_EVALUATE_ROUTE["tags"],
        responses=LOW_INCOME_EVALUATE_ROUTE["responses"],
    )(evaluate_low_income_signal)
    app.post(
        path=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=LOW_INCOME_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_low_income_signal_from_source)
