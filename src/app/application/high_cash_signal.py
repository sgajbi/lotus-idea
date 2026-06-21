from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    HighCashSignalInput,
    HighCashSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationResult,
    SignalEvaluationOutcome,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_high_cash_signal,
)
from app.ports.core_sources import (
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
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


@dataclass(frozen=True)
class EvaluateHighCashFromCoreCommand:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


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


def evaluate_high_cash_signal_from_core(
    command: EvaluateHighCashFromCoreCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = core_source.fetch_high_cash_evidence(
            CoreHighCashEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return evaluate_high_cash_signal_command(
            EvaluateHighCashSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_cash_weight=None,
                portfolio_state_ref=None,
                holdings_ref=None,
                cash_movement_ref=None,
                cashflow_projection_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except CoreSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return evaluate_high_cash_signal_command(
        EvaluateHighCashSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_cash_weight=evidence.source_reported_cash_weight,
            portfolio_state_ref=evidence.portfolio_state_ref,
            holdings_ref=evidence.holdings_ref,
            cash_movement_ref=evidence.cash_movement_ref,
            cashflow_projection_ref=evidence.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
