from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.source_ingestion import (
    HighCashSourceIngestionDecision,
    HighCashSourceIngestionWorkItem,
    IngestHighCashSourceSignalCommand,
    RunHighCashSourceIngestionBatchCommand,
    SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING,
    default_high_cash_source_ingestion_key,
    ingest_high_cash_signal_from_core,
    run_high_cash_source_ingestion_batch,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
)
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence | None = None
    error: Exception | None = None
    seen_request: CoreHighCashEvidenceRequest | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        if self.evidence is None:
            raise AssertionError("evidence must be configured")
        return self.evidence


def source_ref(
    product_id: str,
    *,
    content_hash: str | None = None,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    as_of_date: date = AS_OF_DATE,
    generated_at_utc: datetime = EVALUATED_AT,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=as_of_date,
        generated_at_utc=generated_at_utc,
        content_hash=content_hash or f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def core_evidence(
    *,
    cash_weight: Decimal | None = Decimal("0.18"),
    holdings_hash: str = "sha256:lotus-core:HoldingsAsOf:v1",
    cash_weight_diagnostic: str | None = "core_cash_weight_supported",
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness=freshness),
        holdings_ref=source_ref(
            "lotus-core:HoldingsAsOf:v1",
            content_hash=holdings_hash,
            freshness=freshness,
        ),
        cash_movement_ref=source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1", freshness=freshness
        ),
        cashflow_projection_ref=source_ref(
            "lotus-core:PortfolioCashflowProjection:v1", freshness=freshness
        ),
        cash_weight_diagnostic=cash_weight_diagnostic,
    )


def command(
    *,
    idempotency_key: str | None = None,
    duplicate_of_candidate_id: str | None = None,
) -> IngestHighCashSourceSignalCommand:
    return IngestHighCashSourceSignalCommand(
        portfolio_id=PORTFOLIO_ID,
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        idempotency_key=idempotency_key,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
        correlation_id="corr-source-ingestion",
        trace_id="trace-source-ingestion",
    )


def test_ingests_core_high_cash_candidate_with_generated_source_key() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.ACCEPTED
    assert result.idempotency_key == default_high_cash_source_ingestion_key(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
    )
    assert result.source_authority == "lotus-core"
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.signal_result.persistence is not None
    assert result.signal_result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert result.signal_result.persistence.record is not None
    assert (
        result.signal_result.persistence.record.audit_events[0].actor_subject
        == "signal-ingestion-worker"
    )
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == PORTFOLIO_ID
    assert source.seen_request.correlation_id == "corr-source-ingestion"
    assert source.seen_request.trace_id == "trace-source-ingestion"


def test_source_ingestion_blocks_temporally_mismatched_adapter_evidence_without_persistence() -> None:
    repository = InMemoryIdeaRepository()
    evidence = core_evidence()
    source = RecordingCoreSource(
        evidence=CoreHighCashEvidence(
            source_reported_cash_weight=evidence.source_reported_cash_weight,
            portfolio_state_ref=evidence.portfolio_state_ref,
            holdings_ref=source_ref(
                "lotus-core:HoldingsAsOf:v1",
                as_of_date=date(2026, 6, 20),
            ),
            cash_movement_ref=evidence.cash_movement_ref,
            cashflow_projection_ref=evidence.cashflow_projection_ref,
            cash_weight_diagnostic=evidence.cash_weight_diagnostic,
        )
    )

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.BLOCKED
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.signal_result.persistence is None
    assert result.signal_result.evaluation.unsupported_reasons == (
        UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
    )
    assert repository.snapshot().candidate_records == {}


def test_replays_same_source_ingestion_payload_without_duplicate_candidate() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())
    first = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    replayed = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert first.signal_result.persistence is not None
    assert replayed.decision is HighCashSourceIngestionDecision.REPLAYED
    assert replayed.signal_result.persistence is not None
    assert replayed.signal_result.persistence.record == first.signal_result.persistence.record
    assert len(repository.snapshot().candidate_records) == 1


def test_run_once_batch_ingests_and_replays_duplicate_work_items() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())

    result = run_high_cash_source_ingestion_batch(
        RunHighCashSourceIngestionBatchCommand(
            work_items=(
                HighCashSourceIngestionWorkItem(
                    portfolio_id=PORTFOLIO_ID,
                    as_of_date=AS_OF_DATE,
                ),
                HighCashSourceIngestionWorkItem(
                    portfolio_id=PORTFOLIO_ID,
                    as_of_date=AS_OF_DATE,
                ),
            ),
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT,
            correlation_id="corr-source-worker",
            trace_id="trace-source-worker",
        ),
        core_source=source,
        repository=repository,
    )

    assert result.total_count == 2
    assert result.count(HighCashSourceIngestionDecision.ACCEPTED) == 1
    assert result.count(HighCashSourceIngestionDecision.REPLAYED) == 1
    assert result.decision_counts()["accepted"] == 1
    assert result.decision_counts()["replayed"] == 1
    assert result.item_results[0].idempotency_key == result.item_results[1].idempotency_key
    assert len(repository.snapshot().candidate_records) == 1
    assert source.seen_request is not None
    assert source.seen_request.correlation_id == "corr-source-worker"
    assert source.seen_request.trace_id == "trace-source-worker"


def test_run_once_batch_reports_conflicts_without_duplicate_candidates() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())
    explicit_key = "signal-ingestion:high-cash:lotus-core:batch-conflict"
    work_item = HighCashSourceIngestionWorkItem(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        idempotency_key=explicit_key,
    )

    first = run_high_cash_source_ingestion_batch(
        RunHighCashSourceIngestionBatchCommand(
            work_items=(work_item,),
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT,
        ),
        core_source=source,
        repository=repository,
    )
    source.evidence = core_evidence(holdings_hash="sha256:changed-batch-holdings")
    second = run_high_cash_source_ingestion_batch(
        RunHighCashSourceIngestionBatchCommand(
            work_items=(work_item,),
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT,
        ),
        core_source=source,
        repository=repository,
    )

    assert first.count(HighCashSourceIngestionDecision.ACCEPTED) == 1
    assert second.count(HighCashSourceIngestionDecision.CONFLICT) == 1
    assert len(repository.snapshot().candidate_records) == 1


def test_detects_source_ingestion_conflict_when_same_key_has_new_source_identity() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())
    explicit_key = "signal-ingestion:high-cash:lotus-core:conflict"
    ingest_high_cash_signal_from_core(
        command(idempotency_key=explicit_key),
        core_source=source,
        repository=repository,
    )
    source.evidence = core_evidence(holdings_hash="sha256:changed-holdings")

    conflict = ingest_high_cash_signal_from_core(
        command(idempotency_key=explicit_key),
        core_source=source,
        repository=repository,
    )

    assert conflict.decision is HighCashSourceIngestionDecision.CONFLICT
    assert conflict.signal_result.persistence is not None
    assert conflict.signal_result.persistence.decision is CandidatePersistenceDecision.CONFLICT
    assert conflict.signal_result.persistence.audit_event is None
    assert len(repository.snapshot().candidate_records) == 1


def test_blocks_source_ingestion_when_core_is_unavailable_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(error=CoreSourceUnavailable(code="upstream_timeout"))

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.BLOCKED
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.signal_result.evaluation.unsupported_reasons == (
        UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,
    )
    assert result.signal_result.persistence is None
    assert result.signal_result.source_diagnostic_codes == ("upstream_timeout",)
    assert len(repository.snapshot().candidate_records) == 0


def test_blocks_source_ingestion_when_core_denies_entitlement_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(error=CoreSourceEntitlementDenied())

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.BLOCKED
    assert result.signal_result.evaluation.unsupported_reasons == (
        UnsupportedEvidenceReason.ENTITLEMENT_DENIED,
    )
    assert result.signal_result.persistence is None
    assert result.signal_result.source_diagnostic_codes == ("core_source_entitlement_denied",)
    assert len(repository.snapshot().candidate_records) == 0


def test_blocks_source_ingestion_with_core_cash_weight_diagnostic_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(
        evidence=core_evidence(
            cash_weight=None,
            cash_weight_diagnostic="core_cash_weight_blocked_missing_denominator",
        )
    )

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.BLOCKED
    assert result.signal_result.evaluation.unsupported_reasons == (
        UnsupportedEvidenceReason.MISSING_SOURCE,
    )
    assert result.signal_result.source_diagnostic_codes == (
        "core_cash_weight_blocked_missing_denominator",
    )
    assert result.signal_result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_blocks_source_ingestion_when_core_freshness_is_unproven_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence(freshness=EvidenceFreshness.UNAVAILABLE))

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.BLOCKED
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.signal_result.evaluation.unsupported_reasons == (
        UnsupportedEvidenceReason.STALE_SOURCE,
    )
    assert result.signal_result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_skips_below_threshold_source_ingestion_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence(cash_weight=Decimal("0.05")))

    result = ingest_high_cash_signal_from_core(
        command(),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.SKIPPED_NOT_ELIGIBLE
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.signal_result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_suppresses_duplicate_source_candidate_without_persisting() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())

    result = ingest_high_cash_signal_from_core(
        command(duplicate_of_candidate_id="idea_high_cash_existing"),
        core_source=source,
        repository=repository,
    )

    assert result.decision is HighCashSourceIngestionDecision.SUPPRESSED
    assert result.signal_result.evaluation.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.signal_result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_validates_run_once_batch_boundaries() -> None:
    valid_item = HighCashSourceIngestionWorkItem(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
    )
    mutable_work_items = [valid_item]
    command = RunHighCashSourceIngestionBatchCommand(
        work_items=mutable_work_items,
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )
    mutable_work_items.append(valid_item)

    assert command.work_items == (valid_item,)

    invalid_cases: tuple[
        tuple[Callable[[], RunHighCashSourceIngestionBatchCommand], str],
        ...,
    ] = (
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
            ),
            "work_items must not be empty",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item,),
                tenant_id="tenant-a",
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            "evaluated_at_utc must be timezone-aware",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item,),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                max_items=0,
            ),
            "max_items must be positive",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item,),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                max_items=SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING + 1,
            ),
            "max_items exceeds source_ingestion_run_once_batch_ceiling",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item,) * (SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING + 1),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                max_items=SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING,
            ),
            "work_items exceeds source_ingestion_run_once_batch_ceiling",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item, valid_item),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                max_items=1,
            ),
            "work_items exceeds max_items",
        ),
        (
            lambda: RunHighCashSourceIngestionBatchCommand(
                work_items=(valid_item,),
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                actor_subject=" ",
            ),
            "actor_subject is required",
        ),
    )
    for invalid_command_factory, message in invalid_cases:
        try:
            invalid_command_factory()
        except ValueError as exc:
            assert str(exc) == message
        else:
            raise AssertionError(f"expected {message}")


def test_validates_source_ingestion_identity_fields() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=core_evidence())

    for invalid_command, message in (
        (
            IngestHighCashSourceSignalCommand(
                portfolio_id=" ",
                tenant_id="tenant-a",
                as_of_date=AS_OF_DATE,
                evaluated_at_utc=EVALUATED_AT,
            ),
            "portfolio_id is required",
        ),
        (
            IngestHighCashSourceSignalCommand(
                portfolio_id=PORTFOLIO_ID,
                tenant_id="tenant-a",
                as_of_date=AS_OF_DATE,
                evaluated_at_utc=EVALUATED_AT,
                actor_subject=" ",
            ),
            "actor_subject is required",
        ),
        (
            IngestHighCashSourceSignalCommand(
                portfolio_id=PORTFOLIO_ID,
                tenant_id="tenant-a",
                as_of_date=AS_OF_DATE,
                evaluated_at_utc=EVALUATED_AT,
                idempotency_key=" ",
            ),
            "idempotency_key is required",
        ),
    ):
        try:
            ingest_high_cash_signal_from_core(
                invalid_command,
                core_source=source,
                repository=repository,
            )
        except ValueError as exc:
            assert str(exc) == message
        else:
            raise AssertionError(f"expected {message}")
