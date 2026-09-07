from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.domain import (
    CandidatePresentationReceipt,
    IdeaCandidate,
    OpportunityFamily,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
)
from app.infrastructure.migrations import MigrationDirection
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.integration.postgres_runtime_support import execute_migrations
from tests.support.opportunity_effectiveness_fixture import (
    candidate_fixture,
    record_fixture,
    snapshot_fixture,
)


def test_postgres_presentation_receipt_preserves_global_rank_and_is_tenant_fenced(
    postgres_database_url: str,
) -> None:
    candidate = candidate_fixture(
        "candidate-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id="tenant-a",
    )
    receipt = _receipt(rank_at_presentation=25, visible_candidate_count=1)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(snapshot_fixture(record_fixture(candidate)))
        accepted = repository.record_presentation_receipt(receipt)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(Any, connection))
        replayed = restarted.record_presentation_receipt(receipt)
        conflict = restarted.record_presentation_receipt(_receipt(rank_at_presentation=3))
        with pytest.raises(PresentationReceiptCandidateStateError):
            restarted.record_presentation_receipt(
                _receipt(receipt_id="receipt-presentation-other-tenant", tenant_id="tenant-b")
            )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS receipt_count,
                       COUNT(recorded_at_utc) AS receipt_with_recorded_time_count,
                       MAX(rank_at_presentation) AS rank_at_presentation,
                       MAX(visible_candidate_count) AS visible_candidate_count
                FROM idea_candidate_presentation_receipt
                """
            )
            persisted = cursor.fetchall()[0]

    assert accepted.decision is PresentationReceiptDecision.ACCEPTED
    assert replayed.decision is PresentationReceiptDecision.REPLAYED
    assert replayed.receipt == receipt
    assert conflict.decision is PresentationReceiptDecision.CONFLICT
    assert conflict.receipt == receipt
    assert persisted["receipt_count"] == 1
    assert persisted["receipt_with_recorded_time_count"] == 1
    assert persisted["rank_at_presentation"] == 25
    assert persisted["visible_candidate_count"] == 1


def test_postgres_presentation_receipt_same_raw_key_is_independent_across_tenants(
    postgres_database_url: str,
) -> None:
    candidate_a = _candidate(tenant_id="tenant-a")
    candidate_b = _candidate(
        candidate_id="candidate-presentation-002",
        tenant_id="tenant-b",
    )
    receipt_a = _receipt()
    receipt_b = _receipt(
        candidate_id=candidate_b.candidate_id,
        tenant_id="tenant-b",
        source_revision_vector_digest=(candidate_b.evidence_packet.source_revision_vector_digest),
        source_cut_posture=candidate_b.evidence_packet.source_cut_posture,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(
            snapshot_fixture(record_fixture(candidate_a), record_fixture(candidate_b))
        )
        accepted_a = repository.record_presentation_receipt(receipt_a)
        accepted_b = repository.record_presentation_receipt(receipt_b)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(Any, connection))
        replayed_a = restarted.record_presentation_receipt(receipt_a)
        replayed_b = restarted.record_presentation_receipt(receipt_b)
        conflict_b = restarted.record_presentation_receipt(
            _receipt(
                candidate_id=candidate_b.candidate_id,
                tenant_id="tenant-b",
                rank_at_presentation=3,
                source_revision_vector_digest=(
                    candidate_b.evidence_packet.source_revision_vector_digest
                ),
                source_cut_posture=candidate_b.evidence_packet.source_cut_posture,
            )
        )
        cross_wired = restarted.presentation_receipt_by_id(
            receipt_a.receipt_id,
            candidate_id=receipt_a.candidate_id,
            tenant_id="tenant-b",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tenant_id, candidate_id, rank_at_presentation
                FROM idea_candidate_presentation_receipt
                WHERE receipt_id = %s
                ORDER BY tenant_id
                """,
                (receipt_a.receipt_id,),
            )
            persisted = cursor.fetchall()

    assert accepted_a.decision is PresentationReceiptDecision.ACCEPTED
    assert accepted_b.decision is PresentationReceiptDecision.ACCEPTED
    assert replayed_a.receipt == receipt_a
    assert replayed_b.receipt == receipt_b
    assert conflict_b.decision is PresentationReceiptDecision.CONFLICT
    assert conflict_b.receipt == receipt_b
    assert cross_wired is None
    assert persisted == [
        {
            "tenant_id": "tenant-a",
            "candidate_id": receipt_a.candidate_id,
            "rank_at_presentation": 2,
        },
        {
            "tenant_id": "tenant-b",
            "candidate_id": receipt_b.candidate_id,
            "rank_at_presentation": 2,
        },
    ]


def test_postgres_presentation_receipt_concurrent_replay_is_scoped_by_tenant(
    postgres_database_url: str,
) -> None:
    candidate_a = _candidate(tenant_id="tenant-a")
    candidate_b = _candidate(
        candidate_id="candidate-presentation-002",
        tenant_id="tenant-b",
    )
    receipt_a = _receipt()
    receipt_b = _receipt(
        candidate_id=candidate_b.candidate_id,
        tenant_id="tenant-b",
        source_revision_vector_digest=(candidate_b.evidence_packet.source_revision_vector_digest),
        source_cut_posture=candidate_b.evidence_packet.source_cut_posture,
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        PostgresIdeaRepository(cast(Any, connection)).replace_snapshot(
            snapshot_fixture(record_fixture(candidate_a), record_fixture(candidate_b))
        )

    def record(receipt: CandidatePresentationReceipt) -> PresentationReceiptDecision:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            return (
                PostgresIdeaRepository(cast(Any, connection))
                .record_presentation_receipt(receipt)
                .decision
            )

    with ThreadPoolExecutor(max_workers=4) as executor:
        decisions = tuple(executor.map(record, (receipt_a, receipt_a, receipt_b, receipt_b)))

    assert decisions.count(PresentationReceiptDecision.ACCEPTED) == 2
    assert decisions.count(PresentationReceiptDecision.REPLAYED) == 2
    # A distinct name: `connection` is already bound in this scope to a
    # dict_row connection, so reusing it makes the tuple comparison below
    # unreachable to the type checker even though it is correct at runtime.
    with psycopg.connect(postgres_database_url) as counting_connection:
        assert counting_connection.execute(
            "SELECT COUNT(*) FROM idea_candidate_presentation_receipt"
        ).fetchone() == (2,)


def test_postgres_snapshot_replacement_clears_receipts_before_candidates(
    postgres_database_url: str,
) -> None:
    candidate = candidate_fixture(
        "candidate-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id="tenant-a",
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(snapshot_fixture(record_fixture(candidate)))
        repository.record_presentation_receipt(_receipt())

        repository.replace_snapshot(snapshot_fixture())

        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                       (SELECT COUNT(*) FROM idea_candidate_presentation_receipt)
                           AS receipt_count,
                       (SELECT COUNT(*) FROM idea_candidate_record) AS candidate_count"""
            )
            remaining = cursor.fetchone()

    assert remaining is not None
    assert remaining["receipt_count"] == 0
    assert remaining["candidate_count"] == 0


def test_postgres_rank_migration_rollback_fails_closed_for_independent_rank(
    postgres_database_url: str,
) -> None:
    candidate = candidate_fixture(
        "candidate-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id="tenant-a",
    )
    receipt = _receipt(rank_at_presentation=25, visible_candidate_count=1)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(snapshot_fixture(record_fixture(candidate)))
        repository.record_presentation_receipt(receipt)

    with pytest.raises(psycopg.errors.CheckViolation):
        execute_migrations(postgres_database_url, MigrationDirection.ROLLBACK)

    with psycopg.connect(postgres_database_url) as connection:
        persisted = connection.execute(
            """
            SELECT rank_at_presentation, visible_candidate_count
            FROM idea_candidate_presentation_receipt
            WHERE receipt_id = %s
            """,
            (receipt.receipt_id,),
        ).fetchone()
        active_constraint = connection.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'idea_candidate_presentation_receipt'::regclass
              AND conname = 'ck_idea_candidate_presentation_receipt_values_v3'
            """
        ).fetchone()

    assert persisted == (25, 1)
    assert active_constraint == ("ck_idea_candidate_presentation_receipt_values_v3",)


def _receipt(**overrides: Any) -> CandidatePresentationReceipt:
    candidate = _candidate()
    values: dict[str, Any] = {
        "receipt_id": "receipt-presentation-001",
        "candidate_id": "candidate-presentation-001",
        "tenant_id": "tenant-a",
        "presented_at_utc": datetime(2026, 8, 30, 12, tzinfo=UTC),
        "rank_at_presentation": 2,
        "visible_candidate_count": 7,
        "queue_snapshot_digest": f"sha256:{'a' * 64}",
        "queue_policy_version": "idea-review-queue-v1",
        "ranking_policy_version": "idea-score-v2",
        "candidate_material_version": 1,
        "candidate_evidence_version": 1,
        "source_revision_vector_digest": candidate.evidence_packet.source_revision_vector_digest,
        "source_cut_posture": candidate.evidence_packet.source_cut_posture,
        "accepted_at_utc": datetime(2026, 8, 30, 12, tzinfo=UTC),
    }
    values.update(overrides)
    return CandidatePresentationReceipt(**values)


def _candidate(
    *,
    candidate_id: str = "candidate-presentation-001",
    tenant_id: str = "tenant-a",
) -> IdeaCandidate:
    return candidate_fixture(
        candidate_id,
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id=tenant_id,
    )
