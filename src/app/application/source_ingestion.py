from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.application.high_cash_signal import (
    DEFAULT_HIGH_CASH_POLICY,
    EvaluateAndPersistHighCashFromCoreCommand,
    EvaluateHighCashFromCoreCommand,
    HighCashSignalPersistenceResult,
    evaluate_and_persist_high_cash_signal_from_core,
)
from app.domain import (
    CandidatePersistenceDecision,
    HighCashSignalPolicy,
    SignalEvaluationOutcome,
)
from app.ports.core_sources import CoreOpportunitySourcePort
from app.ports.idea_repository import CandidatePersistenceRepository


SOURCE_INGESTION_ACTOR = "signal-ingestion-worker"


class HighCashSourceIngestionDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    SKIPPED_NOT_ELIGIBLE = "skipped_not_eligible"
    BLOCKED = "blocked"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class IngestHighCashSourceSignalCommand:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    actor_subject: str = SOURCE_INGESTION_ACTOR
    idempotency_key: str | None = None
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class HighCashSourceIngestionResult:
    decision: HighCashSourceIngestionDecision
    signal_result: HighCashSignalPersistenceResult
    idempotency_key: str
    source_authority: str = "lotus-core"


def ingest_high_cash_signal_from_core(
    command: IngestHighCashSourceSignalCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    repository: CandidatePersistenceRepository,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> HighCashSourceIngestionResult:
    _require_text(command.portfolio_id, "portfolio_id")
    _require_text(command.actor_subject, "actor_subject")
    if command.idempotency_key is not None:
        _require_text(command.idempotency_key, "idempotency_key")

    idempotency_key = command.idempotency_key or default_high_cash_source_ingestion_key(
        portfolio_id=command.portfolio_id,
        as_of_date=command.as_of_date,
    )
    signal_result = evaluate_and_persist_high_cash_signal_from_core(
        EvaluateAndPersistHighCashFromCoreCommand(
            evaluation=EvaluateHighCashFromCoreCommand(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            ),
            idempotency_key=idempotency_key,
            actor_subject=command.actor_subject,
        ),
        core_source=core_source,
        repository=repository,
        policy=policy,
    )
    return HighCashSourceIngestionResult(
        decision=_source_ingestion_decision(signal_result),
        signal_result=signal_result,
        idempotency_key=idempotency_key,
    )


def default_high_cash_source_ingestion_key(*, portfolio_id: str, as_of_date: date) -> str:
    _require_text(portfolio_id, "portfolio_id")
    return f"signal-ingestion:high-cash:lotus-core:{portfolio_id}:{as_of_date.isoformat()}"


def _source_ingestion_decision(
    signal_result: HighCashSignalPersistenceResult,
) -> HighCashSourceIngestionDecision:
    if signal_result.persistence is not None:
        return _persistence_decision(signal_result.persistence.decision)
    if signal_result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED:
        return HighCashSourceIngestionDecision.BLOCKED
    if signal_result.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE:
        return HighCashSourceIngestionDecision.SKIPPED_NOT_ELIGIBLE
    if signal_result.evaluation.outcome is SignalEvaluationOutcome.SUPPRESSED:
        return HighCashSourceIngestionDecision.SUPPRESSED
    raise RuntimeError("candidate-created source ingestion result was not persisted")


def _persistence_decision(
    decision: CandidatePersistenceDecision,
) -> HighCashSourceIngestionDecision:
    if decision is CandidatePersistenceDecision.ACCEPTED:
        return HighCashSourceIngestionDecision.ACCEPTED
    if decision is CandidatePersistenceDecision.REPLAYED:
        return HighCashSourceIngestionDecision.REPLAYED
    if decision is CandidatePersistenceDecision.CONFLICT:
        return HighCashSourceIngestionDecision.CONFLICT
    return HighCashSourceIngestionDecision.DUPLICATE_CANDIDATE


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
