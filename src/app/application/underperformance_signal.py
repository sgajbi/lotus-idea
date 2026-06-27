from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnderperformanceSignalInput,
    UnderperformanceSignalPolicy,
    UnsupportedEvidenceReason,
    evaluate_underperformance_signal,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.performance_sources import (
    PerformanceOpportunitySourcePort,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


@dataclass(frozen=True)
class EvaluateUnderperformanceSignalCommand:
    as_of_date: date
    source_reported_active_return: Decimal | None
    benchmark_context_available: bool
    performance_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateUnderperformanceFromPerformanceCommand:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_UNDERPERFORMANCE_POLICY = UnderperformanceSignalPolicy(
    policy_version="underperformance-review-v1",
    active_return_threshold=Decimal("-0.005"),
    candidate_score=Decimal("74"),
)


def evaluate_underperformance_signal_command(
    command: EvaluateUnderperformanceSignalCommand,
    *,
    policy: UnderperformanceSignalPolicy = DEFAULT_UNDERPERFORMANCE_POLICY,
) -> SignalEvaluationResult:
    source_input = UnderperformanceSignalInput(
        as_of_date=command.as_of_date,
        source_reported_active_return=command.source_reported_active_return,
        benchmark_context_available=command.benchmark_context_available,
        performance_ref=command.performance_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_underperformance_signal(source_input, policy)


def evaluate_underperformance_signal_from_performance(
    command: EvaluateUnderperformanceFromPerformanceCommand,
    *,
    performance_source: PerformanceOpportunitySourcePort,
    policy: UnderperformanceSignalPolicy = DEFAULT_UNDERPERFORMANCE_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = performance_source.fetch_underperformance_evidence(
            PerformanceUnderperformanceEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                period_name=command.period_name,
                evaluated_at_utc=command.evaluated_at_utc,
                active_return_threshold=policy.active_return_threshold,
                reporting_currency=command.reporting_currency,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except PerformanceSourceEntitlementDenied:
        return evaluate_underperformance_signal_command(
            EvaluateUnderperformanceSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_active_return=None,
                benchmark_context_available=False,
                performance_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=_portfolio_only_scope(command.portfolio_id),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except PerformanceSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_underperformance_evidence(command, evidence, policy=policy)


def _evaluate_underperformance_evidence(
    command: EvaluateUnderperformanceFromPerformanceCommand,
    evidence: PerformanceUnderperformanceEvidence,
    *,
    policy: UnderperformanceSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_underperformance_signal_command(
        EvaluateUnderperformanceSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_active_return=evidence.source_reported_active_return,
            benchmark_context_available=evidence.benchmark_context_available,
            performance_ref=evidence.performance_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=_portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _portfolio_only_scope(portfolio_id: str) -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="unknown",
        book_id="unknown",
        portfolio_id=portfolio_id,
        client_id="unknown",
    )
