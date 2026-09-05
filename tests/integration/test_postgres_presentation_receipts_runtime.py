from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.domain import (
    CandidatePresentationReceipt,
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
              AND conname = 'ck_idea_candidate_presentation_receipt_values_v2'
            """
        ).fetchone()

    assert persisted == (25, 1)
    assert active_constraint == ("ck_idea_candidate_presentation_receipt_values_v2",)


def _receipt(**overrides: Any) -> CandidatePresentationReceipt:
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
        "accepted_at_utc": datetime(2026, 8, 30, 12, tzinfo=UTC),
    }
    values.update(overrides)
    return CandidatePresentationReceipt(**values)
