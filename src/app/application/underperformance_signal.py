from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidatePersistenceResult,
    CandidateScorePolicyVersion,
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
from app.application.access_scope import portfolio_only_scope
from app.application.candidate_persistence_identity import build_candidate_idempotency_payload
from app.domain.access_scope import ReviewAccessScope
from app.ports.idea_repository import CandidatePersistenceRepository
from app.ports.performance_sources import (
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
    PerformanceUnderperformanceSourcePort,
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


@dataclass(frozen=True)
class EvaluateAndPersistUnderperformanceFromPerformanceCommand:
    evaluation: EvaluateUnderperformanceFromPerformanceCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class UnderperformanceSignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    source_diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _UnderperformanceSourceEvaluation:
    evaluation: SignalEvaluationResult
    source_diagnostic_codes: tuple[str, ...] = ()


DEFAULT_UNDERPERFORMANCE_POLICY = UnderperformanceSignalPolicy(
    policy_version=CandidateScorePolicyVersion.UNDERPERFORMANCE.value,
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
    performance_source: PerformanceUnderperformanceSourcePort,
    policy: UnderperformanceSignalPolicy = DEFAULT_UNDERPERFORMANCE_POLICY,
) -> SignalEvaluationResult:
    return _evaluate_underperformance_source(
        command,
        performance_source=performance_source,
        policy=policy,
    ).evaluation


def evaluate_and_persist_underperformance_signal_from_performance(
    command: EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    *,
    performance_source: PerformanceUnderperformanceSourcePort,
    repository: CandidatePersistenceRepository,
    policy: UnderperformanceSignalPolicy = DEFAULT_UNDERPERFORMANCE_POLICY,
) -> UnderperformanceSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    source_evaluation = _evaluate_underperformance_source(
        command.evaluation,
        performance_source=performance_source,
        policy=policy,
    )
    evaluation = source_evaluation.evaluation
    if evaluation.candidate is None:
        return UnderperformanceSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=build_candidate_idempotency_payload(
            portfolio_id=command.evaluation.portfolio_id,
            as_of_date=command.evaluation.as_of_date,
            period_name=command.evaluation.period_name,
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
            family=OpportunityFamily.UNDERPERFORMANCE,
            policy_version=policy.policy_version,
            evaluation=evaluation,
        ),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return UnderperformanceSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
    )


def _evaluate_underperformance_source(
    command: EvaluateUnderperformanceFromPerformanceCommand,
    *,
    performance_source: PerformanceUnderperformanceSourcePort,
    policy: UnderperformanceSignalPolicy,
) -> _UnderperformanceSourceEvaluation:
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
        return _UnderperformanceSourceEvaluation(
            evaluation=evaluate_underperformance_signal_command(
                EvaluateUnderperformanceSignalCommand(
                    as_of_date=command.as_of_date,
                    source_reported_active_return=None,
                    benchmark_context_available=False,
                    performance_ref=None,
                    evaluated_at_utc=command.evaluated_at_utc,
                    entitlement_allowed=False,
                    access_scope=portfolio_only_scope(command.portfolio_id),
                    duplicate_of_candidate_id=command.duplicate_of_candidate_id,
                ),
                policy=policy,
            ),
            source_diagnostic_codes=("performance_source_entitlement_denied",),
        )
    except PerformanceSourceUnavailable as exc:
        return _UnderperformanceSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.UNDERPERFORMANCE,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=(exc.code,),
        )

    return _UnderperformanceSourceEvaluation(
        evaluation=_evaluate_underperformance_evidence(command, evidence, policy=policy),
        source_diagnostic_codes=_performance_source_diagnostic_codes(evidence),
    )


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
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _performance_source_diagnostic_codes(
    evidence: PerformanceUnderperformanceEvidence,
) -> tuple[str, ...]:
    diagnostic = evidence.performance_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
