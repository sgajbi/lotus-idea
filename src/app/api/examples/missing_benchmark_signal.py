from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import serialize_signal_evaluation
from app.api.missing_benchmark_signals import (
    EvaluateMissingBenchmarkFromSourceRequest,
    EvaluateMissingBenchmarkSignalRequest,
    EvaluateMissingBenchmarkSignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.missing_benchmark_signal import (
    evaluate_missing_benchmark_signal_command,
    evaluate_missing_benchmark_signal_from_core,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBenchmarkAssignmentSourcePort,
    CoreSourceUnavailable,
)


MISSING_BENCHMARK_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/missing-benchmark/evaluate"
MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/missing-benchmark/evaluate-from-source"
)
MISSING_BENCHMARK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "A missing, inactive, ineffective, or unversioned benchmark creates an advisor-review candidate",
    "blocked": "Stale, incomplete, denied, or unavailable Core evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "A current, active, effective, versioned benchmark creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
_TENANT_ID = "tenant-example"
_SOURCE_AUTHORITY = SourceSystem.LOTUS_CORE


@dataclass(frozen=True)
class _ExampleCoreBenchmarkAssignmentSource(CoreBenchmarkAssignmentSourcePort):
    """Deterministic Core-port fake used only by source-backed OpenAPI factories."""

    evidence: CoreBenchmarkAssignmentEvidence
    error: CoreSourceUnavailable | None = None

    def fetch_benchmark_assignment_evidence(
        self,
        request: CoreBenchmarkAssignmentEvidenceRequest,
    ) -> CoreBenchmarkAssignmentEvidence:
        del request
        if self.error is not None:
            raise self.error
        return self.evidence


def build_missing_benchmark_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_missing_benchmark_existing"
        ),
        "notEligible": _caller_evaluation_response(
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="ACTIVE",
            assignment_version_present=True,
        ),
    }


def build_source_backed_missing_benchmark_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=CoreSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_missing_benchmark_existing"
        ),
        "notEligible": _source_evaluation_response(
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="ACTIVE",
            assignment_version_present=True,
        ),
    }


def apply_missing_benchmark_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            MISSING_BENCHMARK_EVALUATE_OPERATION_PATH,
            build_missing_benchmark_evaluation_response_examples(),
        ),
        (
            MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_missing_benchmark_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                MISSING_BENCHMARK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    benchmark_identity_resolved: bool = False,
    assignment_effective_for_as_of_date: bool = False,
    assignment_status: str = "ACTIVE",
    assignment_version_present: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingBenchmarkSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        benchmarkAssignmentRef=_benchmark_assignment_ref(freshness=freshness),
        benchmarkIdentityResolved=benchmark_identity_resolved,
        assignmentEffectiveForAsOfDate=assignment_effective_for_as_of_date,
        assignmentStatus=assignment_status,
        assignmentVersionPresent=assignment_version_present,
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_missing_benchmark_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    benchmark_identity_resolved: bool = False,
    assignment_effective_for_as_of_date: bool = False,
    assignment_status: str = "ACTIVE",
    assignment_version_present: bool = True,
    duplicate_of_candidate_id: str | None = None,
    source_error: CoreSourceUnavailable | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingBenchmarkFromSourceRequest(
        portfolioId=_PORTFOLIO_ID,
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        reportingCurrency="USD",
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    result = evaluate_missing_benchmark_signal_from_core(
        request.to_command(
            tenant_id=_TENANT_ID,
            correlation_id="corr-example",
            trace_id="trace-example",
        ),
        core_source=_ExampleCoreBenchmarkAssignmentSource(
            evidence=_core_evidence(
                benchmark_identity_resolved=benchmark_identity_resolved,
                assignment_effective_for_as_of_date=assignment_effective_for_as_of_date,
                assignment_status=assignment_status,
                assignment_version_present=assignment_version_present,
            ),
            error=source_error,
        ),
    )
    return _serialized(result)


def _core_evidence(
    *,
    benchmark_identity_resolved: bool,
    assignment_effective_for_as_of_date: bool,
    assignment_status: str,
    assignment_version_present: bool,
) -> CoreBenchmarkAssignmentEvidence:
    return CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=_benchmark_assignment_ref().to_domain(),
        benchmark_identity_resolved=benchmark_identity_resolved,
        assignment_effective_for_as_of_date=assignment_effective_for_as_of_date,
        assignment_status=assignment_status,
        assignment_version_present=assignment_version_present,
        assignment_diagnostic="core_benchmark_assignment_benchmark_identity_missing",
        entitlement_allowed=True,
    )


def _benchmark_assignment_ref(
    *, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRefRequest:
    return SourceRefRequest(
        productId="lotus-core:BenchmarkAssignment:v1",
        sourceSystem=_SOURCE_AUTHORITY,
        productVersion="v1",
        route=f"/integration/portfolios/{_PORTFOLIO_ID}/benchmark-assignment",
        asOfDate=_AS_OF_DATE,
        generatedAtUtc=_EVALUATED_AT,
        contentHash="sha256:missing-benchmark-review",
        dataQualityStatus="complete",
        freshness=freshness,
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateMissingBenchmarkSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


__all__ = [
    "MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "MISSING_BENCHMARK_EVALUATE_OPERATION_PATH",
    "MISSING_BENCHMARK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_missing_benchmark_signal_openapi_examples",
    "build_missing_benchmark_evaluation_response_examples",
    "build_source_backed_missing_benchmark_evaluation_response_examples",
]
