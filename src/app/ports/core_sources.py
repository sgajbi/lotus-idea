from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.domain import SourceRef


PORTFOLIO_STATE_PRODUCT_ID = "lotus-core:PortfolioStateSnapshot:v1"
HOLDINGS_PRODUCT_ID = "lotus-core:HoldingsAsOf:v1"
CASH_MOVEMENT_PRODUCT_ID = "lotus-core:PortfolioCashMovementSummary:v1"
CASHFLOW_PROJECTION_PRODUCT_ID = "lotus-core:PortfolioCashflowProjection:v1"
CORE_HIGH_CASH_SOURCE_PRODUCT_IDS = (
    PORTFOLIO_STATE_PRODUCT_ID,
    HOLDINGS_PRODUCT_ID,
    CASH_MOVEMENT_PRODUCT_ID,
    CASHFLOW_PROJECTION_PRODUCT_ID,
)


class CoreSourceUnavailable(Exception):
    def __init__(self, *, code: str = "core_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class CoreSourceEntitlementDenied(Exception):
    pass


def _validate_core_request_scope(*, portfolio_id: str, tenant_id: str) -> None:
    if not portfolio_id.strip():
        raise ValueError("portfolio_id is required")
    if not tenant_id.strip():
        raise ValueError("tenant_id is required")


def _require_aware_evaluation_time(evaluated_at_utc: datetime) -> None:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class CoreHighCashEvidenceRequest:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_core_request_scope(portfolio_id=self.portfolio_id, tenant_id=self.tenant_id)
        _require_aware_evaluation_time(self.evaluated_at_utc)


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
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_core_request_scope(portfolio_id=self.portfolio_id, tenant_id=self.tenant_id)
        _require_aware_evaluation_time(self.evaluated_at_utc)


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
class CorePortfolioStateEvidenceRequest:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_core_request_scope(portfolio_id=self.portfolio_id, tenant_id=self.tenant_id)
        _require_aware_evaluation_time(self.evaluated_at_utc)


@dataclass(frozen=True)
class CorePortfolioStateEvidence:
    portfolio_state_ref: SourceRef | None
    source_evidence_available: bool
    response_product_name: str | None = None
    response_product_version: str | None = None
    response_tenant_id: str | None = None
    response_portfolio_id: str | None = None
    snapshot_mode: str | None = None
    request_fingerprint: str | None = None
    snapshot_id: str | None = None
    source_batch_fingerprint: str | None = None
    response_content_hash: str | None = None
    response_source_digest: str | None = None
    restatement_version: str | None = None
    reconciliation_status: str | None = None
    latest_evidence_at_utc: datetime | None = None
    source_evidence_current: bool = False
    policy_version: str | None = None
    source_correlation_id: str | None = None
    applied_sections: tuple[str, ...] = ()
    dropped_sections: tuple[str, ...] = ()
    portfolio_state_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class CoreLowIncomeEvidenceRequest:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    horizon_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_core_request_scope(portfolio_id=self.portfolio_id, tenant_id=self.tenant_id)
        if self.horizon_days < 1 or self.horizon_days > 366:
            raise ValueError("horizon_days must be between 1 and 366")
        _require_aware_evaluation_time(self.evaluated_at_utc)


@dataclass(frozen=True)
class CoreLowIncomeEvidence:
    source_reported_min_projected_cumulative_cashflow: Decimal | None
    cash_movement_count: int | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    cashflow_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class CoreBondMaturityEvidenceRequest:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    maturity_window_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _validate_core_request_scope(portfolio_id=self.portfolio_id, tenant_id=self.tenant_id)
        if self.maturity_window_days < 1 or self.maturity_window_days > 366:
            raise ValueError("maturity_window_days must be between 1 and 366")
        _require_aware_evaluation_time(self.evaluated_at_utc)


@dataclass(frozen=True)
class CoreBondMaturityEvidence:
    source_reported_next_maturity_date: date | None
    source_reported_maturing_position_count: int | None
    holdings_ref: SourceRef | None
    maturity_fact_ref: SourceRef | None
    maturity_diagnostic: str | None = None
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


class CorePortfolioStateSourcePort(Protocol):
    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        """Fetch source-owned Core portfolio state evidence for opportunity context."""


class CoreLowIncomeSourcePort(Protocol):
    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        """Fetch source-owned Core cashflow evidence for low-income/liquidity review."""


class CoreBondMaturitySourcePort(Protocol):
    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        """Fetch source-owned Core maturity evidence for bond maturity review."""
