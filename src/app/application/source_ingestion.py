from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
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
DEFAULT_SOURCE_INGESTION_BATCH_LIMIT = 100
SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING = 100


class SourceIngestionBatchLimitExceeded(ValueError):
    """Raised when run-once source ingestion exceeds the service-owned ceiling."""


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
    tenant_id: str
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


@dataclass(frozen=True)
class HighCashSourceIngestionWorkItem:
    portfolio_id: str
    as_of_date: date
    idempotency_key: str | None = None
    duplicate_of_candidate_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.portfolio_id, "portfolio_id")
        if self.idempotency_key is not None:
            _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class RunHighCashSourceIngestionBatchCommand:
    work_items: Sequence[HighCashSourceIngestionWorkItem]
    tenant_id: str
    evaluated_at_utc: datetime
    actor_subject: str = SOURCE_INGESTION_ACTOR
    max_items: int = DEFAULT_SOURCE_INGESTION_BATCH_LIMIT
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.actor_subject, "actor_subject")
        work_items = tuple(self.work_items)
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if self.max_items < 1:
            raise ValueError("max_items must be positive")
        if self.max_items > SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING:
            raise SourceIngestionBatchLimitExceeded(
                "max_items exceeds source_ingestion_run_once_batch_ceiling"
            )
        if not work_items:
            raise ValueError("work_items must not be empty")
        if len(work_items) > SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING:
            raise SourceIngestionBatchLimitExceeded(
                "work_items exceeds source_ingestion_run_once_batch_ceiling"
            )
        if len(work_items) > self.max_items:
            raise ValueError("work_items exceeds max_items")
        object.__setattr__(self, "work_items", work_items)


@dataclass(frozen=True)
class HighCashSourceIngestionBatchResult:
    item_results: tuple[HighCashSourceIngestionResult, ...]
    source_authority: str = "lotus-core"

    @property
    def total_count(self) -> int:
        return len(self.item_results)

    def count(self, decision: HighCashSourceIngestionDecision) -> int:
        return sum(1 for result in self.item_results if result.decision is decision)

    def decision_counts(self) -> dict[str, int]:
        counts = Counter(result.decision.value for result in self.item_results)
        return {
            decision.value: counts[decision.value] for decision in HighCashSourceIngestionDecision
        }


def ingest_high_cash_signal_from_core(
    command: IngestHighCashSourceSignalCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    repository: CandidatePersistenceRepository,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> HighCashSourceIngestionResult:
    _require_text(command.portfolio_id, "portfolio_id")
    _require_text(command.tenant_id, "tenant_id")
    _require_text(command.actor_subject, "actor_subject")
    if command.idempotency_key is not None:
        _require_text(command.idempotency_key, "idempotency_key")

    idempotency_key = command.idempotency_key or default_high_cash_source_ingestion_key(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
        as_of_date=command.as_of_date,
    )
    signal_result = evaluate_and_persist_high_cash_signal_from_core(
        EvaluateAndPersistHighCashFromCoreCommand(
            evaluation=EvaluateHighCashFromCoreCommand(
                portfolio_id=command.portfolio_id,
                tenant_id=command.tenant_id,
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


def run_high_cash_source_ingestion_batch(
    command: RunHighCashSourceIngestionBatchCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    repository: CandidatePersistenceRepository,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> HighCashSourceIngestionBatchResult:
    item_results = tuple(
        ingest_high_cash_signal_from_core(
            IngestHighCashSourceSignalCommand(
                portfolio_id=item.portfolio_id,
                tenant_id=command.tenant_id,
                as_of_date=item.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                actor_subject=command.actor_subject,
                idempotency_key=item.idempotency_key,
                duplicate_of_candidate_id=item.duplicate_of_candidate_id,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            ),
            core_source=core_source,
            repository=repository,
            policy=policy,
        )
        for item in command.work_items
    )
    return HighCashSourceIngestionBatchResult(item_results=item_results)


def default_high_cash_source_ingestion_key(
    *,
    tenant_id: str,
    portfolio_id: str,
    as_of_date: date,
) -> str:
    _require_text(tenant_id, "tenant_id")
    _require_text(portfolio_id, "portfolio_id")
    return (
        f"signal-ingestion:high-cash:lotus-core:{tenant_id}:{portfolio_id}:{as_of_date.isoformat()}"
    )


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
