from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    BondMaturitySignalInput,
    BondMaturitySignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_bond_maturity_signal,
)
from app.application.access_scope import portfolio_only_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateBondMaturitySignalCommand:
    as_of_date: date
    source_reported_next_maturity_date: date | None
    source_reported_maturing_position_count: int | None
    holdings_ref: SourceRef | None
    maturity_fact_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateBondMaturityFromCoreCommand:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    maturity_window_days: int = 30
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_BOND_MATURITY_POLICY = BondMaturitySignalPolicy(
    policy_version="bond-maturity-review-v1",
    maturity_window_days=30,
    candidate_score=Decimal("70"),
)


def evaluate_bond_maturity_signal_command(
    command: EvaluateBondMaturitySignalCommand,
    *,
    policy: BondMaturitySignalPolicy = DEFAULT_BOND_MATURITY_POLICY,
) -> SignalEvaluationResult:
    return evaluate_bond_maturity_signal(
        BondMaturitySignalInput(
            as_of_date=command.as_of_date,
            source_reported_next_maturity_date=command.source_reported_next_maturity_date,
            source_reported_maturing_position_count=(
                command.source_reported_maturing_position_count
            ),
            holdings_ref=command.holdings_ref,
            maturity_fact_ref=command.maturity_fact_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=command.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy,
    )


def evaluate_bond_maturity_signal_from_core(
    command: EvaluateBondMaturityFromCoreCommand,
    *,
    core_source: CoreBondMaturitySourcePort,
    policy: BondMaturitySignalPolicy = DEFAULT_BOND_MATURITY_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = core_source.fetch_bond_maturity_evidence(
            CoreBondMaturityEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                maturity_window_days=command.maturity_window_days,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return evaluate_bond_maturity_signal_command(
            EvaluateBondMaturitySignalCommand(
                as_of_date=command.as_of_date,
                source_reported_next_maturity_date=None,
                source_reported_maturing_position_count=None,
                holdings_ref=None,
                maturity_fact_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=portfolio_only_scope(command.portfolio_id),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except CoreSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.BOND_MATURITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_bond_maturity_core_evidence(command, evidence, policy=policy)


def _evaluate_bond_maturity_core_evidence(
    command: EvaluateBondMaturityFromCoreCommand,
    evidence: CoreBondMaturityEvidence,
    *,
    policy: BondMaturitySignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_bond_maturity_signal_command(
        EvaluateBondMaturitySignalCommand(
            as_of_date=command.as_of_date,
            source_reported_next_maturity_date=evidence.source_reported_next_maturity_date,
            source_reported_maturing_position_count=(
                evidence.source_reported_maturing_position_count
            ),
            holdings_ref=evidence.holdings_ref,
            maturity_fact_ref=evidence.maturity_fact_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
