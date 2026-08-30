from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    ReviewAccessScope,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_protocols import PostgresConnection
from app.infrastructure.migrations import (
    MigrationDirection,
    discover_migrations,
    migration_statements,
)
from app.infrastructure.postgres_codecs import idea_candidate_to_json
from app.domain.evidence_hashing import evidence_hash_for_candidate
from tests.integration.postgres_runtime_support import run_concurrent_repository_mutations


def test_postgres_runtime_serializes_candidate_identity_and_idempotency_races(
    postgres_database_url: str,
) -> None:
    candidate = _high_cash_candidate("postgres-concurrent-candidate-same-key")

    same_key_results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: repository.persist_candidate(
            candidate,
            idempotency_key=key,
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        ),
        ("candidate:postgres-concurrent-same-key",) * 2,
    )

    assert {result.decision for result in same_key_results} == {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.REPLAYED,
    }

    duplicate_candidate = _high_cash_candidate("postgres-concurrent-candidate-different-keys")
    different_key_results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: repository.persist_candidate(
            duplicate_candidate,
            idempotency_key=key,
            payload={"candidateId": duplicate_candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        ),
        ("candidate:postgres-concurrent-first", "candidate:postgres-concurrent-second"),
    )

    assert {result.decision for result in different_key_results} == {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
    }
    assert _table_count(postgres_database_url, "idea_candidate_record") == 2
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 3
    assert _table_count(postgres_database_url, "idea_audit_event") == 2
    assert _table_count(postgres_database_url, "idea_outbox_event") == 2


def test_postgres_runtime_serializes_concurrent_evidence_corrections(
    postgres_database_url: str,
) -> None:
    candidate = _high_cash_candidate("concurrent-evidence-correction")
    corrected = _high_cash_candidate(
        "concurrent-evidence-correction",
        cashflow_hash="sha256:corrected-cashflow",
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        accepted = repository.persist_candidate(
            candidate,
            idempotency_key="candidate:correction:initial",
            payload={"candidateId": candidate.candidate_id, "sourceVersion": "initial"},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )
    assert accepted.decision is CandidatePersistenceDecision.ACCEPTED

    correction_results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: repository.persist_candidate(
            corrected,
            idempotency_key=key,
            payload={"candidateId": corrected.candidate_id, "sourceVersion": "corrected"},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
        ),
        ("candidate:correction:first", "candidate:correction:second"),
    )

    try:
        assert {result.decision for result in correction_results} == {
            CandidatePersistenceDecision.EVIDENCE_REFRESHED,
            CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
        }
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            record = PostgresIdeaRepository(
                cast(PostgresConnection, connection)
            ).candidate_record_by_id(candidate.candidate_id)
        assert record is not None
        assert record.candidate.identity.material_version == 1
        assert record.candidate.identity.evidence_version == 2
        assert len(record.version_history) == 2
        assert _table_count(postgres_database_url, "idea_candidate_record") == 1
        assert _table_count(postgres_database_url, "idea_candidate_version_history") == 2
        assert _table_count(postgres_database_url, "idea_idempotency_record") == 3
        assert _table_count(postgres_database_url, "idea_audit_event") == 2
        assert _table_count(postgres_database_url, "idea_outbox_event") == 2
    finally:
        _remove_version_events_from_disposable_test_database(postgres_database_url)


def test_candidate_identity_migration_backfills_existing_rows_deterministically(
    postgres_database_url: str,
) -> None:
    candidate = _high_cash_candidate("legacy-backfill")
    candidate_payload = idea_candidate_to_json(candidate)
    candidate_payload.pop("identity")
    evidence_hash = evidence_hash_for_candidate(candidate)
    migration = discover_migrations(Path(__file__).resolve().parents[3] / "migrations")[-1]

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            for statement in migration_statements(migration, MigrationDirection.ROLLBACK):
                cursor.execute(statement)
            cursor.execute(
                """
                INSERT INTO idea_candidate_record (
                    candidate_id, family, lifecycle_status, review_posture,
                    evidence_packet_id, evidence_hash, candidate_json,
                    persisted_at_utc, updated_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    candidate.candidate_id,
                    candidate.family.value,
                    candidate.lifecycle_status.value,
                    candidate.review_posture.value,
                    candidate.evidence_packet.evidence_packet_id,
                    evidence_hash,
                    Jsonb(candidate_payload),
                    candidate.created_at_utc,
                    candidate.updated_at_utc,
                ),
            )
            for statement in migration_statements(migration, MigrationDirection.APPLY):
                cursor.execute(statement)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        record = (
            PostgresIdeaRepository(cast(PostgresConnection, connection))
            .snapshot()
            .candidate_records[candidate.candidate_id]
        )

    assert record.candidate.identity.business_identity_id == (
        f"opportunity_migrated_{candidate.candidate_id}"
    )
    assert record.candidate.identity.policy_version == "idea-opportunity-identity-migration-v1"
    assert record.candidate.identity.material_fingerprint == evidence_hash
    assert record.candidate.identity.material_version == 1
    assert record.candidate.identity.evidence_version == 1
    assert record.candidate.identity.change_reason.value == "migration_backfill"
    assert len(record.version_history) == 1
    assert record.version_history[0].evidence_hash == evidence_hash


def _high_cash_candidate(
    scope_suffix: str,
    *,
    cashflow_hash: str | None = None,
) -> IdeaCandidate:
    evaluated_at = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    product_ids = (
        "lotus-core:PortfolioStateSnapshot:v1",
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    )
    source_refs = tuple(
        SourceRef(
            product_id=product_id,
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route=f"/source/{product_id}",
            as_of_date=date(2026, 6, 21),
            generated_at_utc=evaluated_at,
            content_hash=(
                cashflow_hash
                if product_id == "lotus-core:PortfolioCashflowProjection:v1"
                and cashflow_hash is not None
                else f"sha256:{product_id}"
            ),
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )
        for product_id in product_ids
    )
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=date(2026, 6, 21),
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=source_refs[0],
            holdings_ref=source_refs[1],
            cash_movement_ref=source_refs[2],
            cashflow_projection_ref=source_refs[3],
            evaluated_at_utc=evaluated_at,
            access_scope=ReviewAccessScope(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id=f"PB_SG_GLOBAL_BAL_001:{scope_suffix}",
                client_id="client-001",
            ),
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    assert result.candidate is not None
    return result.candidate


def _table_count(database_url: str, table_name: str) -> int:
    allowed_tables = {
        "idea_candidate_record",
        "idea_candidate_version_history",
        "idea_idempotency_record",
        "idea_audit_event",
        "idea_outbox_event",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported test table: {table_name}")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


def _remove_version_events_from_disposable_test_database(database_url: str) -> None:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM idea_outbox_event
            WHERE event_type IN (
                'idea.candidate.evidence_refreshed.v1',
                'idea.candidate.material_version_created.v1',
                'idea.candidate.recurrent_condition_reopened.v1'
            )
            """
        )
