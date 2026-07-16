from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.application.runtime_evidence import require_aware
from app.domain import (
    PERFORMANCE_BENCHMARK_READINESS_POLICY_VERSION,
    PerformanceBenchmarkReadinessAssessment,
    assess_performance_benchmark_readiness,
)
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceBenchmarkReadinessSourcePort,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluatePerformanceBenchmarkReadiness:
    tenant_id: str
    book_id: str
    portfolio_id: str
    client_id: str
    evaluation_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        required = {
            "tenant_id": self.tenant_id,
            "book_id": self.book_id,
            "portfolio_id": self.portfolio_id,
            "client_id": self.client_id,
            "evaluation_id": self.evaluation_id,
            "period_name": self.period_name,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
        }
        for name, value in required.items():
            if value is None or not value.strip():
                raise ValueError(f"{name} is required")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        if self.reporting_currency is not None and (
            len(self.reporting_currency.strip()) != 3
            or not self.reporting_currency.strip().isalpha()
        ):
            raise ValueError("reporting_currency must be a three-letter currency code")


@dataclass(frozen=True)
class PerformanceBenchmarkReadinessResult:
    command: EvaluatePerformanceBenchmarkReadiness
    evidence: PerformanceBenchmarkReadinessEvidence | None
    assessment: PerformanceBenchmarkReadinessAssessment | None
    source_error_code: str | None
    policy_version: str = PERFORMANCE_BENCHMARK_READINESS_POLICY_VERSION


def evaluate_performance_benchmark_readiness(
    command: EvaluatePerformanceBenchmarkReadiness,
    *,
    performance_source: PerformanceBenchmarkReadinessSourcePort,
) -> PerformanceBenchmarkReadinessResult:
    try:
        evidence = performance_source.fetch_benchmark_readiness_evidence(
            PerformanceBenchmarkReadinessEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                period_name=command.period_name,
                evaluated_at_utc=command.evaluated_at_utc,
                reporting_currency=command.reporting_currency,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except PerformanceSourceEntitlementDenied:
        return PerformanceBenchmarkReadinessResult(
            command=command,
            evidence=None,
            assessment=None,
            source_error_code="performance_source_entitlement_denied",
        )
    except PerformanceSourceUnavailable as exc:
        return PerformanceBenchmarkReadinessResult(
            command=command,
            evidence=None,
            assessment=None,
            source_error_code=exc.code,
        )
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=evidence.benchmark_context_available,
        benchmark_id=evidence.benchmark_id,
        benchmark_return_source=evidence.benchmark_return_source,
    )
    return PerformanceBenchmarkReadinessResult(
        command=command,
        evidence=evidence,
        assessment=assessment,
        source_error_code=None,
    )
