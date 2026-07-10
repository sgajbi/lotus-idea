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
    RiskConcentrationSourceRuntime,
    RiskConcentrationSourceRuntimeBlocker,
)
from app.api.runtime_dependencies import (
    build_risk_concentration_source_runtime_from_environment as _build_risk_concentration_source_runtime_from_environment,
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
from app.application.concentration_risk_signal import (
    EvaluateConcentrationRiskFromRiskCommand,
    EvaluateConcentrationRiskSignalCommand,
    evaluate_concentration_risk_signal_from_risk,
    evaluate_concentration_risk_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


def _is_risk_concentration_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, RiskConcentrationSourceRuntimeBlocker)


class EvaluateConcentrationRiskSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Risk concentration evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    top_position_weight_current: Decimal | None = Field(
        default=None,
        alias="topPositionWeightCurrent",
        ge=Decimal("0"),
        le=Decimal("1"),
        description=(
            "Top single-position weight reported by the Risk concentration source. "
            "lotus-idea does not calculate concentration weights."
        ),
        examples=["0.18"],
    )
    top_issuer_weight_current: Decimal | None = Field(
        default=None,
        alias="topIssuerWeightCurrent",
        ge=Decimal("0"),
        le=Decimal("1"),
        description=(
            "Top issuer or counterparty weight reported by the Risk concentration "
            "source. lotus-idea does not calculate issuer exposure."
        ),
        examples=["0.24"],
    )
    issuer_coverage_status: str | None = Field(
        default=None,
        alias="issuerCoverageStatus",
        description=(
            "Source-owned issuer coverage posture. The current foundation accepts "
            "`complete` before creating a review candidate."
        ),
        examples=["complete"],
    )
    concentration_ref: SourceRefRequest | None = Field(
        default=None,
        alias="concentrationRef",
        description="Source-owned Lotus Risk concentration report reference.",
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
        examples=["idea_concentration_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateConcentrationRiskSignalCommand:
        return EvaluateConcentrationRiskSignalCommand(
            as_of_date=self.as_of_date,
            top_position_weight_current=self.top_position_weight_current,
            top_issuer_weight_current=self.top_issuer_weight_current,
            issuer_coverage_status=self.issuer_coverage_status,
            concentration_ref=(
                self.concentration_ref.to_domain() if self.concentration_ref is not None else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateConcentrationRiskFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Lotus Risk concentration evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Lotus Risk concentration evidence.",
        examples=["2026-06-21"],
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
        examples=["idea_concentration_existing"],
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
    ) -> EvaluateConcentrationRiskFromRiskCommand:
        return EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateConcentrationRiskSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_concentration_risk_signal(
    request: EvaluateConcentrationRiskSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateConcentrationRiskSignalResponse | JSONResponse:
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
        evaluator=evaluate_concentration_risk_signal_command,
        response_factory=EvaluateConcentrationRiskSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_concentration_risk_signal_from_source(
    request: Request,
    signal_request: EvaluateConcentrationRiskFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateConcentrationRiskSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_RISK.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        runtime_factory=_build_risk_concentration_source_runtime_from_environment,
        is_runtime_blocked=_is_risk_concentration_runtime_blocked,
        blocked_detail="Risk source runtime is not configured for concentration source evaluation.",
        command_factory=lambda runtime: signal_request.to_command(
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_concentration_risk_signal_from_risk(
            command,
            risk_source=cast(RiskConcentrationSourceRuntime, runtime).risk_source,
        ),
        response_factory=EvaluateConcentrationRiskSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


def _source_ref_contracts(
    request: EvaluateConcentrationRiskSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.concentration_ref,
            SourceSystem.LOTUS_RISK,
            ("lotus-risk:ConcentrationRiskReport:v1",),
        ),
    )


CONCENTRATION_RISK_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/concentration-risk/evaluate",
    "operation_id": "evaluateConcentrationRiskIdeaSignal",
    "summary": "Evaluate a concentration risk idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Lotus Risk concentration evidence "
        "for single-position or issuer concentration review posture. The endpoint "
        "is a bounded API foundation; it does not fetch upstream sources, calculate "
        "concentration, approve risk methodology, recommend trades, create rebalance "
        "actions, publish client communication, certify a data product, or promote a "
        "supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateConcentrationRiskSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Concentration signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "concentration",
                        "reasonCodes": ["concentration_attention", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_concentration_8d57adbf52f7f5a7",
                            "family": "concentration",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_concentration_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "78",
                            "scorePolicyVersion": "concentration-attention-v1",
                            "sourceSignalIds": ["signal_concentration_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-risk:ConcentrationRiskReport:v1",
                                    "sourceSystem": "lotus-risk",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "quality_passed",
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


CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
    "operation_id": "evaluateConcentrationRiskIdeaSignalFromSource",
    "summary": "Evaluate a concentration risk idea signal from Lotus Risk",
    "description": (
        "Fetches source-owned Lotus Risk ConcentrationRiskReport evidence through the "
        "configured Risk source adapter, then evaluates deterministic concentration "
        "review posture. The endpoint does not persist candidates, calculate "
        "concentration, approve risk methodology, recommend trades, create rebalance "
        "actions, certify live source support, create Gateway/Workbench support, "
        "publish client communication, certify a data product, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateConcentrationRiskSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: CONCENTRATION_RISK_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Risk source runtime is not configured for concentration source evaluation.",
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


def register_concentration_risk_signal_routes(app: FastAPI) -> None:
    app.post(
        path=CONCENTRATION_RISK_EVALUATE_ROUTE["path"],
        operation_id=CONCENTRATION_RISK_EVALUATE_ROUTE["operation_id"],
        summary=CONCENTRATION_RISK_EVALUATE_ROUTE["summary"],
        description=CONCENTRATION_RISK_EVALUATE_ROUTE["description"],
        status_code=CONCENTRATION_RISK_EVALUATE_ROUTE["status_code"],
        response_model=CONCENTRATION_RISK_EVALUATE_ROUTE["response_model"],
        tags=CONCENTRATION_RISK_EVALUATE_ROUTE["tags"],
        responses=CONCENTRATION_RISK_EVALUATE_ROUTE["responses"],
    )(evaluate_concentration_risk_signal)
    app.post(
        path=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_concentration_risk_signal_from_source)
