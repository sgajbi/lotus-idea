from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.domain import SourceRef


class RiskSourceUnavailable(Exception):
    def __init__(self, *, code: str = "risk_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class RiskSourceEntitlementDenied(Exception):
    pass


@dataclass(frozen=True)
class RiskConcentrationEvidenceRequest:
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
class RiskConcentrationEvidence:
    top_position_weight_current: Decimal | None
    top_issuer_weight_current: Decimal | None
    issuer_coverage_status: str | None
    concentration_ref: SourceRef | None
    concentration_diagnostic: str | None = None
    entitlement_allowed: bool = True


class RiskOpportunitySourcePort(Protocol):
    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        """Fetch source-owned Lotus Risk concentration evidence for idea evaluation."""
