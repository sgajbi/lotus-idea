from __future__ import annotations

from datetime import date, datetime
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import service_unavailable_metadata
from app.api.runtime_dependencies import (
    CoreBondMaturitySourceRuntime,
    CoreBondMaturitySourceRuntimeBlocker,
)
from app.api.runtime_dependencies import (
    build_core_bond_maturity_source_runtime_from_environment as _build_core_bond_maturity_source_runtime_from_environment,
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
from app.application.bond_maturity_signal import (
    EvaluateBondMaturityFromCoreCommand,
    EvaluateBondMaturitySignalCommand,
    evaluate_bond_maturity_signal_from_core,
    evaluate_bond_maturity_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


def _is_core_bond_maturity_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, CoreBondMaturitySourceRuntimeBlocker)


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
            "Next maturity date reported by the caller-supplied Core maturity evidence. lotus-idea "
            "does not calculate maturity schedules or replacement recommendations."
        ),
        examples=["2026-07-10"],
    )
    source_reported_maturing_position_count: int | None = Field(
        default=None,
        alias="sourceReportedMaturingPositionCount",
        ge=0,
        description="Number of maturing holdings reported by Core PortfolioMaturitySummary evidence.",
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
        description="Source-owned Core PortfolioMaturitySummary reference.",
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
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

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


class EvaluateBondMaturityFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Core maturity source products.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Core maturity source evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    maturity_window_days: int = Field(
        default=30,
        alias="maturityWindowDays",
        ge=1,
        le=366,
        description="Bounded look-forward window passed to Core maturity evidence retrieval.",
        examples=[45],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_bond_maturity_existing"],
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
        tenant_id: str,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> EvaluateBondMaturityFromCoreCommand:
        return EvaluateBondMaturityFromCoreCommand(
            portfolio_id=self.portfolio_id,
            tenant_id=tenant_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            maturity_window_days=self.maturity_window_days,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateBondMaturitySignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_bond_maturity_signal(
    request: EvaluateBondMaturitySignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateBondMaturitySignalResponse | JSONResponse:
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
        evaluator=evaluate_bond_maturity_signal_command,
        response_factory=EvaluateBondMaturitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_bond_maturity_signal_from_source(
    request: Request,
    signal_request: EvaluateBondMaturityFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateBondMaturitySignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_CORE.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        runtime_factory=_build_core_bond_maturity_source_runtime_from_environment,
        is_runtime_blocked=_is_core_bond_maturity_runtime_blocked,
        blocked_detail="Core source runtime is not configured for bond-maturity source evaluation.",
        command_factory=lambda runtime, tenant_id: signal_request.to_command(
            tenant_id=tenant_id or "",
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_bond_maturity_signal_from_core(
            command,
            core_source=cast(CoreBondMaturitySourceRuntime, runtime).core_source,
        ),
        response_factory=EvaluateBondMaturitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
        require_tenant_context=True,
    )


def _source_ref_contracts(
    request: EvaluateBondMaturitySignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.holdings_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:HoldingsAsOf:v1",),
        ),
        SignalSourceRefContract(
            request.maturity_fact_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:PortfolioMaturitySummary:v1",),
        ),
    )


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


BOND_MATURITY_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/bond-maturity/evaluate",
    "operation_id": "evaluateBondMaturityIdeaSignal",
    "summary": "Evaluate a bond maturity idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core PortfolioMaturitySummary evidence "
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
                                },
                                {
                                    "productId": "lotus-core:PortfolioMaturitySummary:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                },
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


BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
    "operation_id": "evaluateBondMaturityIdeaSignalFromSource",
    "summary": "Evaluate a bond maturity idea signal from Core",
    "description": (
        "Fetches source-owned Core PortfolioMaturitySummary and HoldingsAsOf evidence "
        "through the configured Core source adapter, then evaluates deterministic "
        "bond-maturity review posture. The endpoint does not persist candidates, own "
        "maturity schedules, recommend replacement products, calculate reinvestment "
        "advice, approve planning suitability, certify live source support, create "
        "Gateway/Workbench support, create orders, publish client communication, certify "
        "a data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateBondMaturitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: BOND_MATURITY_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Core source runtime is not configured for bond-maturity source evaluation.",
            description="Core source runtime configuration is missing or invalid.",
        ),
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
    app.post(
        path=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=BOND_MATURITY_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_bond_maturity_signal_from_source)
