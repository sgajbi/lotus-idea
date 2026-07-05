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


@dataclass(frozen=True)
class RiskVolatilityEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    volatility_threshold: Decimal
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if not self.period_name.strip():
            raise ValueError("period_name is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if self.volatility_threshold < Decimal("0"):
            raise ValueError("volatility_threshold must be non-negative")


@dataclass(frozen=True)
class RiskVolatilityEvidence:
    source_reported_volatility: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    risk_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class RiskDrawdownEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    drawdown_threshold: Decimal
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if not self.period_name.strip():
            raise ValueError("period_name is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if self.drawdown_threshold > Decimal("0"):
            raise ValueError("drawdown_threshold must be zero or negative")


@dataclass(frozen=True)
class RiskDrawdownEvidence:
    source_reported_max_drawdown: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    risk_diagnostic: str | None = None
    entitlement_allowed: bool = True


@dataclass(frozen=True)
class RiskReturnObservation:
    observation_date: date
    return_value: Decimal


@dataclass(frozen=True)
class RiskMandateHealthContextRequest:
    portfolio_id: str
    as_of_date: date
    period_name: str
    portfolio_open_date: date
    returns: tuple[RiskReturnObservation, ...]
    benchmark_returns: tuple[RiskReturnObservation, ...]
    evaluated_at_utc: datetime
    tracking_error_attention_threshold: Decimal = Decimal("0.05")
    reporting_currency: str | None = None
    net_or_gross: str = "NET"
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if not self.period_name.strip():
            raise ValueError("period_name is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if not self.returns:
            raise ValueError("returns are required")
        if not self.benchmark_returns:
            raise ValueError("benchmark_returns are required")
        if self.tracking_error_attention_threshold < Decimal("0"):
            raise ValueError("tracking_error_attention_threshold must be non-negative")
        if self.net_or_gross not in {"NET", "GROSS"}:
            raise ValueError("net_or_gross must be NET or GROSS")


@dataclass(frozen=True)
class RiskMandateHealthContextEvidence:
    mandate_risk_health_ref: SourceRef
    health_state: str
    threshold_breached: bool | None
    risk_diagnostic: str | None = None
    entitlement_allowed: bool = True


class RiskOpportunitySourcePort(Protocol):
    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        """Fetch source-owned Lotus Risk concentration evidence for idea evaluation."""

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        """Fetch source-owned Lotus Risk volatility evidence for idea evaluation."""

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        """Fetch source-owned Lotus Risk drawdown evidence for idea evaluation."""


class RiskMandateHealthSourcePort(Protocol):
    def fetch_mandate_health_context(
        self, request: RiskMandateHealthContextRequest
    ) -> RiskMandateHealthContextEvidence:
        """Fetch source-owned mandate risk-health context refs for idea evaluation."""
