from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    HighCashSignalInput,
    HighCashSignalPolicy,
    SignalEvaluationResult,
    SourceRef,
    evaluate_high_cash_signal,
)


@dataclass(frozen=True)
class EvaluateHighCashSignalCommand:
    as_of_date: date
    source_reported_cash_weight: Decimal | None
    portfolio_state_ref: SourceRef | None
    holdings_ref: SourceRef | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    duplicate_of_candidate_id: str | None = None


DEFAULT_HIGH_CASH_POLICY = HighCashSignalPolicy(
    policy_version="idle-liquidity-v1",
    cash_weight_threshold=Decimal("0.12"),
    candidate_score=Decimal("82"),
)


def evaluate_high_cash_signal_command(
    command: EvaluateHighCashSignalCommand,
    *,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> SignalEvaluationResult:
    source_input = HighCashSignalInput(
        as_of_date=command.as_of_date,
        source_reported_cash_weight=command.source_reported_cash_weight,
        portfolio_state_ref=command.portfolio_state_ref,
        holdings_ref=command.holdings_ref,
        cash_movement_ref=command.cash_movement_ref,
        cashflow_projection_ref=command.cashflow_projection_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_high_cash_signal(source_input, policy)
