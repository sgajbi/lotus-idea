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


class CoreOpportunitySourcePort(Protocol):
    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        """Fetch source-owned Core evidence for high-cash evaluation."""
