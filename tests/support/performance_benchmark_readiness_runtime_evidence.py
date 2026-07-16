from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.performance_benchmark_readiness import (
    EvaluatePerformanceBenchmarkReadiness,
    evaluate_performance_benchmark_readiness,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (
    build_performance_benchmark_readiness_runtime_execution,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
)

NOW = datetime(2026, 7, 16, 14, 0, tzinfo=UTC)


@dataclass
class AuthoritativePerformanceBenchmarkReadinessSource:
    evidence: PerformanceBenchmarkReadinessEvidence = field(
        default_factory=lambda: performance_benchmark_readiness_evidence()
    )
    requests: list[PerformanceBenchmarkReadinessEvidenceRequest] = field(default_factory=list)
    closed: bool = False

    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        self.requests.append(request)
        return self.evidence

    def close(self) -> None:
        self.closed = True


def performance_benchmark_readiness_command() -> EvaluatePerformanceBenchmarkReadiness:
    return EvaluatePerformanceBenchmarkReadiness(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=NOW.date(),
        period_name="1Y",
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr-performance",
        trace_id="trace-performance",
    )


def performance_benchmark_readiness_evidence(
    *,
    benchmark_context_available: bool = False,
    benchmark_id: str | None = None,
    benchmark_return_source: str | None = None,
    readiness_diagnostic: str = "performance_benchmark_context_missing",
    requested_point_count: int = 120,
    returned_point_count: int = 120,
    missing_point_count: int = 0,
    coverage_ratio: Decimal = Decimal("1"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    data_quality_status: str = "ready",
    response_portfolio_id: str = "portfolio-a",
    producer_correlation_id: str = "corr-performance",
    producer_trace_id: str = "trace-performance",
    as_of_date: date = NOW.date(),
    generated_at_utc: datetime = NOW,
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
            as_of_date=as_of_date,
            generated_at_utc=generated_at_utc,
            content_hash="sha256:" + "1" * 64,
            data_quality_status=data_quality_status,
            freshness=freshness,
        ),
        calculation_id="calculation-a",
        response_portfolio_id=response_portfolio_id,
        input_fingerprint="sha256:" + "2" * 64,
        calculation_hash="sha256:" + "1" * 64,
        requested_point_count=requested_point_count,
        returned_point_count=returned_point_count,
        missing_point_count=missing_point_count,
        coverage_ratio=coverage_ratio,
        producer_correlation_id=producer_correlation_id,
        producer_trace_id=producer_trace_id,
        readiness_diagnostic=readiness_diagnostic,
    )


def performance_benchmark_readiness_runtime_execution(
    *,
    source: AuthoritativePerformanceBenchmarkReadinessSource | None = None,
) -> dict[str, Any]:
    result = evaluate_performance_benchmark_readiness(
        performance_benchmark_readiness_command(),
        performance_source=source or AuthoritativePerformanceBenchmarkReadinessSource(),
    )
    return build_performance_benchmark_readiness_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
