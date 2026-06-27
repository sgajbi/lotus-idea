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
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if not self.period_name.strip():
            raise ValueError("period_name is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
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


class PerformanceOpportunitySourcePort(Protocol):
    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        """Fetch source-owned performance evidence for underperformance idea evaluation."""
