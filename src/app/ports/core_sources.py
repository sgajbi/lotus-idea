from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.domain import SourceRef


class CoreSourceUnavailable(Exception):
    def __init__(self, *, code: str = "core_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class CoreSourceEntitlementDenied(Exception):
    pass


@dataclass(frozen=True)
class CoreHighCashEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class CoreHighCashEvidence:
    source_reported_cash_weight: Decimal | None
    portfolio_state_ref: SourceRef | None
    holdings_ref: SourceRef | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    cash_weight_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class CoreBenchmarkAssignmentEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class CoreBenchmarkAssignmentEvidence:
    benchmark_assignment_ref: SourceRef | None
    benchmark_identity_resolved: bool
    assignment_effective_for_as_of_date: bool
    assignment_status: str | None
    assignment_version_present: bool
    assignment_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class CoreLowIncomeEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    horizon_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if self.horizon_days < 1 or self.horizon_days > 366:
            raise ValueError("horizon_days must be between 1 and 366")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class CoreLowIncomeEvidence:
    source_reported_min_projected_cumulative_cashflow: Decimal | None
    cash_movement_count: int | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    cashflow_diagnostic: str | None = None
    entitlement_allowed: bool = True


class CoreOpportunitySourcePort(Protocol):
    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        """Fetch source-owned Core evidence for high-cash evaluation."""


class CoreBenchmarkAssignmentSourcePort(Protocol):
    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        """Fetch source-owned Core benchmark assignment evidence for opportunity context."""


class CoreLowIncomeSourcePort(Protocol):
    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        """Fetch source-owned Core cashflow evidence for low-income/liquidity review."""
