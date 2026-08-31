from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domain import (
    CandidateChangeReason,
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewAccessScope,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)
from app.domain.opportunity_identity import (
    OPPORTUNITY_IDENTITY_POLICY_VERSION,
    PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION,
)
from app.domain.persistence import CandidatePersistenceDecision
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
SCOPE = ReviewAccessScope(
    tenant_id="tenant-001",
    book_id="book-001",
    portfolio_id="portfolio-001",
    client_id="client-001",
)


def test_postgres_repository_versions_corrected_evidence_on_one_candidate_aggregate() -> None:
    connection = FakePostgresConnection()
    candidate = _high_cash_candidate()
    corrected = _high_cash_candidate(cashflow_hash="sha256:corrected-cashflow")
    _persist(connection, candidate, key="high-cash:001", source_version="original")

    refreshed = _persist(
        connection,
        corrected,
        key="high-cash:002",
        source_version="corrected",
        occurred_at=EVALUATED_AT + timedelta(minutes=5),
    )

    _assert_evidence_refresh(connection, refreshed, corrected)


def test_postgres_repository_keeps_next_day_terminal_evidence_refresh_closed() -> None:
    connection = FakePostgresConnection()
    candidate = replace(
        _high_cash_candidate(),
        lifecycle_status=IdeaLifecycleStatus.CLOSED,
        review_posture=ReviewPosture.NO_ACTION,
    )
    next_day = EVALUATED_AT + timedelta(days=1)
    refreshed_candidate = _high_cash_candidate(
        as_of_date=next_day.date(),
        evaluated_at=next_day,
    )
    _persist(connection, candidate, key="terminal-high-cash:001", source_version="day-one")

    refreshed = _persist(
        connection,
        refreshed_candidate,
        key="terminal-high-cash:002",
        source_version="day-two",
        occurred_at=next_day,
    )

    record = _assert_evidence_refresh(connection, refreshed, refreshed_candidate)
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.CLOSED
    assert record.candidate.review_posture is ReviewPosture.NO_ACTION
    assert record.candidate.identity.change_reason is CandidateChangeReason.EVIDENCE_CORRECTION


def test_postgres_repository_backfills_v2_identity_without_reopening_terminal_candidate() -> None:
    connection = FakePostgresConnection()
    incoming = _high_cash_candidate()
    existing = replace(
        incoming,
        identity=replace(
            incoming.identity,
            policy_version=PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION,
            material_fingerprint=f"sha256:{'b' * 64}",
        ),
        lifecycle_status=IdeaLifecycleStatus.CLOSED,
        review_posture=ReviewPosture.NO_ACTION,
    )
    _persist(connection, existing, key="v2-policy:001", source_version="v2")

    migrated = _persist(
        connection,
        incoming,
        key="v3-policy:001",
        source_version="v3",
        occurred_at=EVALUATED_AT + timedelta(minutes=5),
    )

    record = _assert_evidence_refresh(connection, migrated, incoming)
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.CLOSED
    assert record.candidate.review_posture is ReviewPosture.NO_ACTION
    assert record.candidate.identity.policy_version == OPPORTUNITY_IDENTITY_POLICY_VERSION
    assert record.candidate.identity.material_fingerprint == incoming.identity.material_fingerprint
    assert record.candidate.identity.change_reason is CandidateChangeReason.MIGRATION_BACKFILL


def _high_cash_candidate(
    *,
    cashflow_hash: str | None = None,
    as_of_date: date = AS_OF_DATE,
    evaluated_at: datetime = EVALUATED_AT,
) -> IdeaCandidate:
    refs = _source_refs(
        cashflow_hash=cashflow_hash,
        as_of_date=as_of_date,
        evaluated_at=evaluated_at,
    )
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=as_of_date,
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=evaluated_at,
            access_scope=SCOPE,
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v2",
            cash_weight_threshold=Decimal("0.12"),
        ),
    )
    assert result.candidate is not None
    return result.candidate


def _source_refs(
    *,
    cashflow_hash: str | None,
    as_of_date: date,
    evaluated_at: datetime,
) -> tuple[SourceRef, ...]:
    products = (
        "lotus-core:PortfolioStateSnapshot:v1",
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    )
    return tuple(
        SourceRef(
            product_id=product_id,
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route=f"/source/{product_id}",
            as_of_date=as_of_date,
            generated_at_utc=evaluated_at,
            content_hash=(
                cashflow_hash
                if product_id == products[-1] and cashflow_hash is not None
                else f"sha256:{product_id}:{as_of_date.isoformat()}"
            ),
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )
        for product_id in products
    )


def _persist(
    connection: FakePostgresConnection,
    candidate: IdeaCandidate,
    *,
    key: str,
    source_version: str,
    occurred_at: datetime = EVALUATED_AT,
) -> CandidatePersistenceResult:
    return PostgresIdeaRepository(connection).persist_candidate(
        candidate,
        idempotency_key=f"signal-ingestion:{key}",
        payload={"candidateId": candidate.candidate_id, "sourceVersion": source_version},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=occurred_at,
    )


def _assert_evidence_refresh(
    connection: FakePostgresConnection,
    result: CandidatePersistenceResult,
    candidate: IdeaCandidate,
) -> CandidatePersistenceRecord:
    record = PostgresIdeaRepository(connection).candidate_record_by_id(candidate.candidate_id)
    assert result.decision is CandidatePersistenceDecision.EVIDENCE_REFRESHED
    assert record == result.record
    assert record is not None
    assert record.candidate.identity.material_version == 1
    assert record.candidate.identity.evidence_version == 2
    assert len(record.version_history) == 2
    assert len(connection.rows["idea_candidate_record"]) == 1
    assert len(connection.rows["idea_candidate_version_history"]) == 2
    assert connection.rows["idea_outbox_event"][-1]["event_type"] == (
        "idea.candidate.evidence_refreshed.v1"
    )
    return record
