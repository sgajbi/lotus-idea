from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.signal_models import (
    IdeaCandidateSummaryResponse,
    ReviewAccessScopeRequest,
    SourceRefRequest,
)
from app.api.temporal_validation import require_timezone_aware
from app.api.signal_api_support import (
    RouteMetadata,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_refs,
)
from app.application.missing_benchmark_signal import (
    EvaluateMissingBenchmarkSignalCommand,
    evaluate_missing_benchmark_signal_command,
)
from app.domain import SignalEvaluationResult
from app.observability import emit_foundation_operation_event


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


class EvaluateMissingBenchmarkSignalResponse(CamelModel):
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
    ) -> "EvaluateMissingBenchmarkSignalResponse":
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


async def evaluate_missing_benchmark_signal(
    request: EvaluateMissingBenchmarkSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingBenchmarkSignalResponse | JSONResponse:
    source_authority = source_authority_from_refs((request.benchmark_assignment_ref,))
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

    result = evaluate_missing_benchmark_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateMissingBenchmarkSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


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
