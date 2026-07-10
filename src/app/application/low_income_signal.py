from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    LowIncomeSignalInput,
    LowIncomeSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_low_income_signal,
)
from app.application.access_scope import tenant_portfolio_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateLowIncomeSignalCommand:
    as_of_date: date
    source_reported_min_projected_cumulative_cashflow: Decimal | None
    cash_movement_count: int | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateLowIncomeFromCoreCommand:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    horizon_days: int = 30
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_LOW_INCOME_POLICY = LowIncomeSignalPolicy(
    policy_version="cashflow-liquidity-review-v1",
    projected_cumulative_cashflow_threshold=Decimal("-10000"),
    candidate_score=Decimal("68"),
)


def evaluate_low_income_signal_command(
    command: EvaluateLowIncomeSignalCommand,
    *,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> SignalEvaluationResult:
    return evaluate_low_income_signal(
        LowIncomeSignalInput(
            as_of_date=command.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                command.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=command.cash_movement_count,
            cash_movement_ref=command.cash_movement_ref,
            cashflow_projection_ref=command.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=command.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy,
    )


def evaluate_low_income_signal_from_core(
    command: EvaluateLowIncomeFromCoreCommand,
    *,
    core_source: CoreLowIncomeSourcePort,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = core_source.fetch_low_income_evidence(
            CoreLowIncomeEvidenceRequest(
                portfolio_id=command.portfolio_id,
                tenant_id=command.tenant_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                horizon_days=command.horizon_days,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return evaluate_low_income_signal_command(
            EvaluateLowIncomeSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_min_projected_cumulative_cashflow=None,
                cash_movement_count=None,
                cash_movement_ref=None,
                cashflow_projection_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=tenant_portfolio_scope(
                    tenant_id=command.tenant_id,
                    portfolio_id=command.portfolio_id,
                ),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except CoreSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.LOW_INCOME,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_low_income_core_evidence(command, evidence, policy=policy)


def _evaluate_low_income_core_evidence(
    command: EvaluateLowIncomeFromCoreCommand,
    evidence: CoreLowIncomeEvidence,
    *,
    policy: LowIncomeSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_low_income_signal_command(
        EvaluateLowIncomeSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                evidence.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=evidence.cash_movement_count,
            cash_movement_ref=evidence.cash_movement_ref,
            cashflow_projection_ref=evidence.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=tenant_portfolio_scope(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
            ),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
