from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.domain import SourceRef


class PerformanceSourceUnavailable(Exception):
    def __init__(self, *, code: str = "performance_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class PerformanceSourceEntitlementDenied(Exception):
    pass


@dataclass(frozen=True)
class PerformanceUnderperformanceEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    active_return_threshold: Decimal
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_portfolio_period_request(
            self.portfolio_id, self.period_name, self.evaluated_at_utc
        )
        if self.active_return_threshold < Decimal("-1") or self.active_return_threshold > Decimal(
            "0"
        ):
            raise ValueError("active_return_threshold must be between -1 and 0")


@dataclass(frozen=True)
class PerformanceUnderperformanceEvidence:
    source_reported_active_return: Decimal | None
    benchmark_context_available: bool
    performance_ref: SourceRef | None
    performance_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class PerformanceBenchmarkReadinessEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_portfolio_period_request(
            self.portfolio_id, self.period_name, self.evaluated_at_utc
        )


@dataclass(frozen=True)
class PerformanceBenchmarkReadinessEvidence:
    benchmark_context_available: bool
    benchmark_id: str | None
    benchmark_return_source: str | None
    performance_ref: SourceRef | None
    calculation_id: str
    response_portfolio_id: str
    input_fingerprint: str
    calculation_hash: str
    requested_point_count: int
    returned_point_count: int
    missing_point_count: int
    coverage_ratio: Decimal
    producer_correlation_id: str | None
    producer_trace_id: str | None
    readiness_diagnostic: str
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class PerformanceMandateHealthContextRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    portfolio_period_return: Decimal | None
    benchmark_period_return: Decimal | None
    active_return_attention_threshold: Decimal = Decimal("-0.50")
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_portfolio_period_request(
            self.portfolio_id, self.period_name, self.evaluated_at_utc
        )


@dataclass(frozen=True)
class PerformanceMandateHealthContextEvidence:
    mandate_performance_health_ref: SourceRef
    health_state: str
    threshold_breached: bool | None
    performance_diagnostic: str | None = None
    entitlement_allowed: bool = True


class PerformanceUnderperformanceSourcePort(Protocol):
    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        """Fetch source-owned performance evidence for underperformance idea evaluation."""


class PerformanceOpportunitySourcePort(PerformanceUnderperformanceSourcePort, Protocol):
    """Backward-compatible alias for the underperformance source contract."""


class PerformanceBenchmarkReadinessSourcePort(Protocol):
    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        """Fetch source-owned benchmark-readiness evidence for missing-benchmark review."""


class PerformanceMandateHealthSourcePort(Protocol):
    def fetch_mandate_health_context(
        self,
        request: PerformanceMandateHealthContextRequest,
    ) -> PerformanceMandateHealthContextEvidence:
        """Fetch source-owned mandate performance-health context refs for idea evaluation."""


def _validate_portfolio_period_request(
    portfolio_id: str,
    period_name: str,
    evaluated_at_utc: datetime,
) -> None:
    if not portfolio_id.strip():
        raise ValueError("portfolio_id is required")
    if not period_name.strip():
        raise ValueError("period_name is required")
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")
