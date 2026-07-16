from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.performance_benchmark_readiness import (
    EvaluatePerformanceBenchmarkReadiness,
    evaluate_performance_benchmark_readiness,
)
from app.domain import (
    EvidenceFreshness,
    PerformanceBenchmarkReadinessOutcome,
    SourceRef,
    SourceSystem,
    assess_performance_benchmark_readiness,
)
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
)

NOW = datetime(2026, 7, 16, 14, 0, tzinfo=UTC)


@dataclass
class RecordingPerformanceBenchmarkReadinessSource:
    evidence: PerformanceBenchmarkReadinessEvidence = field(
        default_factory=lambda: performance_evidence()
    )
    error: Exception | None = None
    requests: list[PerformanceBenchmarkReadinessEvidenceRequest] = field(default_factory=list)

    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.evidence


def test_assessment_requires_review_when_performance_has_no_benchmark_context() -> None:
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=False,
        benchmark_id=None,
        benchmark_return_source=None,
    )

    assert assessment.outcome is PerformanceBenchmarkReadinessOutcome.REVIEW_REQUIRED
    assert assessment.diagnostic == "performance_benchmark_context_missing"
    assert assessment.benchmark_review_required is True


def test_assessment_returns_no_opportunity_for_complete_benchmark_context() -> None:
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=True,
        benchmark_id="BMK_BALANCED",
        benchmark_return_source="calculated",
    )

    assert assessment.outcome is PerformanceBenchmarkReadinessOutcome.NO_OPPORTUNITY
    assert assessment.diagnostic == "performance_benchmark_context_ready"
    assert assessment.benchmark_review_required is False


@pytest.mark.parametrize(
    ("available", "benchmark_id", "return_source"),
    (
        (True, None, "calculated"),
        (True, "BMK_BALANCED", None),
        (False, "BMK_BALANCED", None),
        (False, None, "calculated"),
    ),
)
def test_assessment_blocks_inconsistent_context(
    available: bool,
    benchmark_id: str | None,
    return_source: str | None,
) -> None:
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=available,
        benchmark_id=benchmark_id,
        benchmark_return_source=return_source,
    )

    assert assessment.outcome is PerformanceBenchmarkReadinessOutcome.BLOCKED
    assert assessment.diagnostic == "performance_benchmark_context_inconsistent"


def test_use_case_preserves_one_authoritative_performance_result() -> None:
    source = RecordingPerformanceBenchmarkReadinessSource()

    result = evaluate_performance_benchmark_readiness(command(), performance_source=source)

    assert len(source.requests) == 1
    assert result.evidence is source.evidence
    assert result.source_error_code is None
    assert result.assessment is not None
    assert result.assessment.outcome is PerformanceBenchmarkReadinessOutcome.REVIEW_REQUIRED
    assert source.requests[0].portfolio_id == "portfolio-a"
    assert source.requests[0].correlation_id == "corr-performance"
    assert source.requests[0].trace_id == "trace-performance"


def test_use_case_preserves_truthful_no_opportunity_result() -> None:
    source = RecordingPerformanceBenchmarkReadinessSource(
        evidence=performance_evidence(
            benchmark_context_available=True,
            benchmark_id="BMK_BALANCED",
            benchmark_return_source="calculated",
            readiness_diagnostic="performance_benchmark_context_ready",
        )
    )

    result = evaluate_performance_benchmark_readiness(command(), performance_source=source)

    assert len(source.requests) == 1
    assert result.assessment is not None
    assert result.assessment.outcome is PerformanceBenchmarkReadinessOutcome.NO_OPPORTUNITY


@pytest.mark.parametrize(
    ("error", "expected_code"),
    (
        (
            PerformanceSourceUnavailable(code="performance_returns_series_pending"),
            "performance_returns_series_pending",
        ),
        (
            PerformanceSourceEntitlementDenied(),
            "performance_source_entitlement_denied",
        ),
    ),
)
def test_use_case_preserves_stable_source_error(
    error: Exception,
    expected_code: str,
) -> None:
    source = RecordingPerformanceBenchmarkReadinessSource(error=error)

    result = evaluate_performance_benchmark_readiness(command(), performance_source=source)

    assert len(source.requests) == 1
    assert result.evidence is None
    assert result.assessment is None
    assert result.source_error_code == expected_code


def test_command_requires_pseudonymous_receipt_scope() -> None:
    with pytest.raises(ValueError, match="book_id is required"):
        replace(command(), book_id=" ")

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        replace(command(), evaluated_at_utc=datetime(2026, 7, 16, 14, 0))

    with pytest.raises(ValueError, match="reporting_currency must be a three-letter currency code"):
        replace(command(), reporting_currency="US")


def command() -> EvaluatePerformanceBenchmarkReadiness:
    return EvaluatePerformanceBenchmarkReadiness(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=date(2026, 7, 16),
        period_name="1Y",
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr-performance",
        trace_id="trace-performance",
    )


def performance_evidence(
    *,
    benchmark_context_available: bool = False,
    benchmark_id: str | None = None,
    benchmark_return_source: str | None = None,
    readiness_diagnostic: str = "performance_benchmark_context_missing",
) -> PerformanceBenchmarkReadinessEvidence:
    return PerformanceBenchmarkReadinessEvidence(
        benchmark_context_available=benchmark_context_available,
        benchmark_id=benchmark_id,
        benchmark_return_source=benchmark_return_source,
        performance_ref=SourceRef(
            product_id="lotus-performance:ReturnsSeriesBundle:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            product_version="v1",
            route="/integration/returns/series",
            as_of_date=date(2026, 7, 16),
            generated_at_utc=NOW,
            content_hash="sha256:" + "1" * 64,
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        calculation_id="calculation-a",
        response_portfolio_id="portfolio-a",
        input_fingerprint="sha256:" + "2" * 64,
        calculation_hash="sha256:" + "1" * 64,
        requested_point_count=120,
        returned_point_count=120,
        missing_point_count=0,
        coverage_ratio=Decimal("1"),
        producer_correlation_id="corr-performance",
        producer_trace_id="trace-performance",
        readiness_diagnostic=readiness_diagnostic,
    )
