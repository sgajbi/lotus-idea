from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.access_scope import ReviewAccessScope
from app.domain.ideas import (
    IdeaCandidate,
    OpportunityFamily,
    OpportunitySignal,
    ReasonCode,
    SourceRef,
    UnsupportedEvidenceReason,
)


class SignalEvaluationOutcome(StrEnum):
    CANDIDATE_CREATED = "candidate_created"
    NOT_ELIGIBLE = "not_eligible"
    BLOCKED = "blocked"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class HighCashSignalPolicy:
    policy_version: str
    cash_weight_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.cash_weight_threshold < Decimal("0") or self.cash_weight_threshold > Decimal("1"):
            raise ValueError("cash_weight_threshold must be between 0 and 1")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class ConcentrationRiskSignalPolicy:
    policy_version: str
    top_position_weight_threshold: Decimal
    top_issuer_weight_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        for field_name, threshold in (
            ("top_position_weight_threshold", self.top_position_weight_threshold),
            ("top_issuer_weight_threshold", self.top_issuer_weight_threshold),
        ):
            if threshold < Decimal("0") or threshold > Decimal("1"):
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class UnderperformanceSignalPolicy:
    policy_version: str
    active_return_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.active_return_threshold < Decimal("-1") or self.active_return_threshold > Decimal(
            "0"
        ):
            raise ValueError("active_return_threshold must be between -1 and 0")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class MandateHealthSignalPolicy:
    policy_version: str
    minimum_workflow_decision_count: int
    minimum_lineage_edge_count: int
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.minimum_workflow_decision_count < 0:
            raise ValueError("minimum_workflow_decision_count must be non-negative")
        if self.minimum_lineage_edge_count < 0:
            raise ValueError("minimum_lineage_edge_count must be non-negative")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class HighVolatilitySignalPolicy:
    policy_version: str
    volatility_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.volatility_threshold < Decimal("0"):
            raise ValueError("volatility_threshold must be non-negative")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class DrawdownReviewSignalPolicy:
    policy_version: str
    max_drawdown_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.max_drawdown_threshold > Decimal("0"):
            raise ValueError("max_drawdown_threshold must be zero or negative")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class HighCashSignalInput:
    as_of_date: date
    source_reported_cash_weight: Decimal | None
    portfolio_state_ref: SourceRef | None
    holdings_ref: SourceRef | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class ConcentrationRiskSignalInput:
    as_of_date: date
    top_position_weight_current: Decimal | None
    top_issuer_weight_current: Decimal | None
    issuer_coverage_status: str | None
    concentration_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class UnderperformanceSignalInput:
    as_of_date: date
    source_reported_active_return: Decimal | None
    benchmark_context_available: bool
    performance_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class MandateHealthSignalInput:
    as_of_date: date
    workflow_decision_count: int | None
    lineage_edge_count: int | None
    manage_supportability_state: str | None
    portfolio_scope_confirmed: bool
    action_register_ref: SourceRef | None
    evaluated_at_utc: datetime
    mandate_performance_health_ref: SourceRef | None = None
    mandate_risk_health_ref: SourceRef | None = None
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class HighVolatilitySignalInput:
    as_of_date: date
    source_reported_volatility: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class DrawdownReviewSignalInput:
    as_of_date: date
    source_reported_max_drawdown: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class SignalEvaluationResult:
    outcome: SignalEvaluationOutcome
    family: OpportunityFamily
    reason_codes: tuple[ReasonCode, ...]
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...] = ()
    signal: OpportunitySignal | None = None
    candidate: IdeaCandidate | None = None


__all__ = [
    "ConcentrationRiskSignalInput",
    "ConcentrationRiskSignalPolicy",
    "DrawdownReviewSignalInput",
    "DrawdownReviewSignalPolicy",
    "HighCashSignalInput",
    "HighCashSignalPolicy",
    "HighVolatilitySignalInput",
    "HighVolatilitySignalPolicy",
    "MandateHealthSignalInput",
    "MandateHealthSignalPolicy",
    "SignalEvaluationOutcome",
    "SignalEvaluationResult",
    "UnderperformanceSignalInput",
    "UnderperformanceSignalPolicy",
]
