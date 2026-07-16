from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


PERFORMANCE_BENCHMARK_READINESS_POLICY_VERSION = "performance-benchmark-readiness-v1"


class PerformanceBenchmarkReadinessOutcome(StrEnum):
    REVIEW_REQUIRED = "review_required"
    NO_OPPORTUNITY = "no_opportunity"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PerformanceBenchmarkReadinessAssessment:
    outcome: PerformanceBenchmarkReadinessOutcome
    diagnostic: str
    benchmark_review_required: bool


def assess_performance_benchmark_readiness(
    *,
    benchmark_context_available: bool,
    benchmark_id: str | None,
    benchmark_return_source: str | None,
) -> PerformanceBenchmarkReadinessAssessment:
    normalized_benchmark_id = _normalized_optional_text(benchmark_id)
    normalized_return_source = _normalized_optional_text(benchmark_return_source)
    if benchmark_context_available:
        if normalized_benchmark_id is None or normalized_return_source is None:
            return PerformanceBenchmarkReadinessAssessment(
                outcome=PerformanceBenchmarkReadinessOutcome.BLOCKED,
                diagnostic="performance_benchmark_context_inconsistent",
                benchmark_review_required=False,
            )
        return PerformanceBenchmarkReadinessAssessment(
            outcome=PerformanceBenchmarkReadinessOutcome.NO_OPPORTUNITY,
            diagnostic="performance_benchmark_context_ready",
            benchmark_review_required=False,
        )
    if normalized_benchmark_id is not None or normalized_return_source is not None:
        return PerformanceBenchmarkReadinessAssessment(
            outcome=PerformanceBenchmarkReadinessOutcome.BLOCKED,
            diagnostic="performance_benchmark_context_inconsistent",
            benchmark_review_required=False,
        )
    return PerformanceBenchmarkReadinessAssessment(
        outcome=PerformanceBenchmarkReadinessOutcome.REVIEW_REQUIRED,
        diagnostic="performance_benchmark_context_missing",
        benchmark_review_required=True,
    )


def _normalized_optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None
