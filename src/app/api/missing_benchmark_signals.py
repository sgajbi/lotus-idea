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
    CoreBenchmarkAssignmentSourceRuntime,
    CoreBenchmarkAssignmentSourceRuntimeBlocker,
)
from app.api.runtime_dependencies import (
    build_core_benchmark_assignment_source_runtime_from_environment as _build_core_benchmark_assignment_source_runtime_from_environment,
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
from app.application.missing_benchmark_signal import (
    EvaluateMissingBenchmarkFromCoreCommand,
    EvaluateMissingBenchmarkSignalCommand,
    evaluate_missing_benchmark_signal_from_core,
    evaluate_missing_benchmark_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


def _is_core_benchmark_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, CoreBenchmarkAssignmentSourceRuntimeBlocker)


class EvaluateMissingBenchmarkSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Core benchmark-assignment posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    benchmark_assignment_ref: SourceRefRequest | None = Field(
        default=None,
        alias="benchmarkAssignmentRef",
        description="Source-owned Core benchmark-assignment reference.",
    )
    benchmark_identity_resolved: bool = Field(
        ...,
        alias="benchmarkIdentityResolved",
        description="Whether Core reports that the portfolio benchmark identity is resolved.",
    )
    assignment_effective_for_as_of_date: bool = Field(
        ...,
        alias="assignmentEffectiveForAsOfDate",
        description="Whether Core reports that the benchmark assignment is effective for the business date.",
    )
    assignment_status: str | None = Field(
        default=None,
        alias="assignmentStatus",
        description="Source-owned benchmark-assignment status such as ACTIVE, INACTIVE, or BLOCKED.",
        examples=["INACTIVE"],
    )
    assignment_version_present: bool = Field(
        ...,
        alias="assignmentVersionPresent",
        description="Whether Core reports a versioned benchmark assignment is present.",
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
        examples=["idea_missing_benchmark_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateMissingBenchmarkSignalCommand:
        return EvaluateMissingBenchmarkSignalCommand(
            as_of_date=self.as_of_date,
            benchmark_assignment_ref=(
                self.benchmark_assignment_ref.to_domain()
                if self.benchmark_assignment_ref is not None
                else None
            ),
            benchmark_identity_resolved=self.benchmark_identity_resolved,
            assignment_effective_for_as_of_date=self.assignment_effective_for_as_of_date,
            assignment_status=self.assignment_status,
            assignment_version_present=self.assignment_version_present,
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateMissingBenchmarkFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Core benchmark-assignment source products.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Core benchmark-assignment source evidence.",
        examples=["2026-06-21"],
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
        description="Optional reporting currency passed to Core when assignment context is currency-specific.",
        examples=["USD"],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_missing_benchmark_existing"],
    )

    @field_validator("portfolio_id")
    @classmethod
    def _portfolio_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("portfolioId is required")
        return cleaned

    @field_validator("reporting_currency")
    @classmethod
    def _reporting_currency_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("reportingCurrency must not be blank when supplied")
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
    ) -> EvaluateMissingBenchmarkFromCoreCommand:
        return EvaluateMissingBenchmarkFromCoreCommand(
            portfolio_id=self.portfolio_id,
            tenant_id=tenant_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            reporting_currency=self.reporting_currency,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateMissingBenchmarkSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_missing_benchmark_signal(
    request: EvaluateMissingBenchmarkSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingBenchmarkSignalResponse | JSONResponse:
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
        evaluator=evaluate_missing_benchmark_signal_command,
        response_factory=EvaluateMissingBenchmarkSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_missing_benchmark_signal_from_source(
    request: Request,
    signal_request: EvaluateMissingBenchmarkFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingBenchmarkSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_CORE.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=portfolio_only_scope(signal_request.portfolio_id),
        runtime_factory=_build_core_benchmark_assignment_source_runtime_from_environment,
        is_runtime_blocked=_is_core_benchmark_runtime_blocked,
        blocked_detail=(
            "Core source runtime is not configured for missing-benchmark source evaluation."
        ),
        command_factory=lambda runtime, tenant_id: signal_request.to_command(
            tenant_id=tenant_id or "",
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_missing_benchmark_signal_from_core(
            command,
            core_source=cast(CoreBenchmarkAssignmentSourceRuntime, runtime).core_source,
        ),
        response_factory=EvaluateMissingBenchmarkSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
        require_tenant_context=True,
    )


def _source_ref_contracts(
    request: EvaluateMissingBenchmarkSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.benchmark_assignment_ref,
            SourceSystem.LOTUS_CORE,
            ("lotus-core:BenchmarkAssignment:v1",),
        ),
    )


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


MISSING_BENCHMARK_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-benchmark/evaluate",
    "operation_id": "evaluateMissingBenchmarkIdeaSignal",
    "summary": "Evaluate a missing benchmark idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core benchmark-assignment evidence "
        "for missing, inactive, ineffective, or unversioned benchmark posture. The "
        "endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "assign benchmarks, calculate benchmark or portfolio performance, certify "
        "benchmark methodology, publish client communication, certify a data product, "
        "or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingBenchmarkSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Missing benchmark signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "missing_benchmark",
                        "reasonCodes": ["missing_benchmark", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_missing_benchmark_8d57adbf52f7f5a7",
                            "family": "missing_benchmark",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_missing_benchmark_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "missing-benchmark-review-v1",
                            "sourceSignalIds": ["signal_missing_benchmark_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:BenchmarkAssignment:v1",
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


MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
    "operation_id": "evaluateMissingBenchmarkIdeaSignalFromSource",
    "summary": "Evaluate a missing benchmark idea signal from Core",
    "description": (
        "Fetches source-owned Core benchmark-assignment evidence through the configured "
        "Core source adapter after resolving exactly one tenant from trusted caller context "
        "and retaining that tenant in candidate access scope. Request-body tenant overrides "
        "are rejected. It then evaluates deterministic missing-benchmark review "
        "posture. The endpoint does not persist candidates, assign benchmarks, calculate "
        "benchmark or portfolio performance, certify benchmark methodology, certify live "
        "source support, create Gateway/Workbench support, publish client communication, "
        "or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingBenchmarkSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Core-backed missing benchmark signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "missing_benchmark",
                        "reasonCodes": ["missing_benchmark", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_missing_benchmark_8d57adbf52f7f5a7",
                            "family": "missing_benchmark",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_missing_benchmark_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "missing-benchmark-review-v1",
                            "sourceSignalIds": ["signal_missing_benchmark_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:BenchmarkAssignment:v1",
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
            detail="Core source runtime is not configured for missing-benchmark source evaluation.",
            description="Core source runtime configuration is missing or invalid.",
        ),
    },
}


def register_missing_benchmark_signal_routes(app: FastAPI) -> None:
    app.post(
        path=MISSING_BENCHMARK_EVALUATE_ROUTE["path"],
        operation_id=MISSING_BENCHMARK_EVALUATE_ROUTE["operation_id"],
        summary=MISSING_BENCHMARK_EVALUATE_ROUTE["summary"],
        description=MISSING_BENCHMARK_EVALUATE_ROUTE["description"],
        status_code=MISSING_BENCHMARK_EVALUATE_ROUTE["status_code"],
        response_model=MISSING_BENCHMARK_EVALUATE_ROUTE["response_model"],
        tags=MISSING_BENCHMARK_EVALUATE_ROUTE["tags"],
        responses=MISSING_BENCHMARK_EVALUATE_ROUTE["responses"],
    )(evaluate_missing_benchmark_signal)
    app.post(
        path=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_missing_benchmark_signal_from_source)
