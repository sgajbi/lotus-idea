from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.domain import CandidatePresentationReceipt, IdeaCandidate, OpportunityFamily
from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    MigrationExecutionPlan,
    MigrationStep,
    build_migration_plan,
    execute_migration_plan,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.integration.postgres_runtime_support import MIGRATIONS_DIR
from tests.support.opportunity_effectiveness_fixture import (
    candidate_fixture,
    record_fixture,
    snapshot_fixture,
)


def test_tenant_scope_migration_preserves_existing_receipt(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))
    candidate = _candidate("candidate-presentation-a", "tenant-a")
    receipt = _receipt(candidate.candidate_id, "tenant-a")

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        snapshot = snapshot_fixture(record_fixture(candidate))
        snapshot = replace(
            snapshot,
            presentation_receipts={(receipt.tenant_id, receipt.receipt_id): receipt},
        )
        PostgresIdeaRepository(cast(Any, connection)).replace_snapshot(snapshot)

        execute_migration_plan(cast(MigrationConnection, connection), apply)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                -- `constraint` and `position` are reserved words and cannot be
                -- unquoted aliases; the sibling deployment proof uses
                -- `constraint_record` for the same reason. The PostgreSQL gate
                -- now derives its files from fixture use, so this query cannot
                -- silently fall out of the governed runtime lane again.
                SELECT attribute.attname
                FROM pg_constraint AS constraint_record
                CROSS JOIN
                    unnest(constraint_record.conkey)
                    WITH ORDINALITY AS key(attnum, key_position)
                JOIN pg_attribute AS attribute
                  ON attribute.attrelid = constraint_record.conrelid
                 AND attribute.attnum = key.attnum
                WHERE constraint_record.conrelid
                      = 'idea_candidate_presentation_receipt'::regclass
                  AND constraint_record.contype = 'p'
                ORDER BY key.key_position
                """
            )
            primary_key_columns = tuple(row["attname"] for row in cursor.fetchall())

        restarted = PostgresIdeaRepository(cast(Any, connection))
        assert primary_key_columns == ("tenant_id", "receipt_id")
        assert (
            restarted.presentation_receipt_by_id(
                receipt.receipt_id,
                candidate_id=receipt.candidate_id,
                tenant_id=receipt.tenant_id,
            )
            == receipt
        )


def test_tenant_scope_migration_refuses_lossy_rollback(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    candidate_a = _candidate("candidate-presentation-a", "tenant-a")
    candidate_b = _candidate("candidate-presentation-b", "tenant-b")
    receipt_a = _receipt(candidate_a.candidate_id, "tenant-a")
    receipt_b = _receipt(candidate_b.candidate_id, "tenant-b")
    base_snapshot = snapshot_fixture(record_fixture(candidate_a), record_fixture(candidate_b))
    snapshot = replace(
        base_snapshot,
        presentation_receipts={
            (receipt_a.tenant_id, receipt_a.receipt_id): receipt_a,
            (receipt_b.tenant_id, receipt_b.receipt_id): receipt_b,
        },
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        PostgresIdeaRepository(cast(Any, connection)).replace_snapshot(snapshot)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match=(
                "cannot roll back tenant-scoped presentation receipts while duplicate raw keys exist"
            ),
        ):
            execute_migration_plan(cast(MigrationConnection, connection), rollback)

        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM idea_candidate_presentation_receipt")
            assert cursor.fetchone() == {"count": 2}


def _migration() -> MigrationStep:
    return next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "029"
    )


def _candidate(candidate_id: str, tenant_id: str) -> IdeaCandidate:
    return candidate_fixture(
        candidate_id,
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 9, 7, 12, tzinfo=UTC),
        tenant_id=tenant_id,
    )


def _receipt(candidate_id: str, tenant_id: str) -> CandidatePresentationReceipt:
    candidate = _candidate(candidate_id, tenant_id)
    return CandidatePresentationReceipt(
        receipt_id="shared-presentation-key",
        candidate_id=candidate_id,
        tenant_id=tenant_id,
        presented_at_utc=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        rank_at_presentation=2,
        visible_candidate_count=7,
        queue_snapshot_digest=f"sha256:{'a' * 64}",
        queue_policy_version="idea-review-queue-v1",
        ranking_policy_version="idea-score-v2",
        candidate_material_version=1,
        candidate_evidence_version=1,
        source_revision_vector_digest=(candidate.evidence_packet.source_revision_vector_digest),
        source_cut_posture=candidate.evidence_packet.source_cut_posture,
        accepted_at_utc=datetime(2026, 9, 7, 12, 5, 1, tzinfo=UTC),
    )
