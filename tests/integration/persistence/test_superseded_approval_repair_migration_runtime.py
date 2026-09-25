from __future__ import annotations

from typing import cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    MigrationExecutionPlan,
    MigrationStep,
    build_migration_plan,
    execute_migration_plan,
)
from scripts.seed_postgres_disaster_recovery_fixture import seed_disaster_recovery_fixture
from tests.integration.postgres_runtime_support import MIGRATIONS_DIR


APPROVED_CANDIDATE_ID = "idea_dr_fixture_review"
CONVERTED_CANDIDATE_ID = "idea_dr_fixture_conversion"
CORRECTED_EVIDENCE_HASH = "sha256:3a24aceb2ab1104ee61c767fc356f790e6b2c7964c163b566562489873ae74aa"


def test_migration_reopens_only_approved_candidate_with_superseded_exact_authority(
    postgres_database_url: str,
) -> None:
    seed_disaster_recovery_fixture(
        postgres_database_url,
        confirm_disposable_database=True,
    )
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        typed_connection = cast(MigrationConnection, connection)

        # The current exact approval remains authoritative and must not be rewritten.
        execute_migration_plan(typed_connection, rollback)
        execute_migration_plan(typed_connection, apply)
        assert _candidate_state(connection, APPROVED_CANDIDATE_ID) == (
            "approved",
            "approved_for_conversion",
        )
        assert _repair_audit_count(connection, APPROVED_CANDIDATE_ID) == 0

        execute_migration_plan(typed_connection, rollback)
        converted_state = _candidate_state(connection, CONVERTED_CANDIDATE_ID)
        _correct_candidate_evidence_without_new_review(connection)
        execute_migration_plan(typed_connection, apply)

        assert _candidate_state(connection, APPROVED_CANDIDATE_ID) == (
            "ready_for_review",
            "advisor_review_required",
        )
        assert _candidate_json_state(connection, APPROVED_CANDIDATE_ID) == (
            "ready_for_review",
            "advisor_review_required",
            None,
        )
        assert _candidate_state(connection, CONVERTED_CANDIDATE_ID) == converted_state
        assert _repair_audit_count(connection, APPROVED_CANDIDATE_ID) == 1
        assert _repair_transition_count(connection, APPROVED_CANDIDATE_ID) == 1

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="unsafe downgrade: migration 032 reopened candidates",
        ):
            execute_migration_plan(typed_connection, rollback)
        connection.rollback()

        assert _candidate_state(connection, APPROVED_CANDIDATE_ID) == (
            "ready_for_review",
            "advisor_review_required",
        )


def _correct_candidate_evidence_without_new_review(
    connection: psycopg.Connection[dict[str, object]],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE idea_candidate_record
            SET evidence_version = evidence_version + 1,
                evidence_hash = %s,
                change_reason = 'evidence_correction',
                candidate_json = jsonb_set(
                    jsonb_set(
                        candidate_json,
                        '{identity,evidence_version}',
                        to_jsonb(evidence_version + 1)
                    ),
                    '{identity,change_reason}',
                    to_jsonb('evidence_correction'::TEXT)
                )
            WHERE candidate_id = %s
            """,
            (CORRECTED_EVIDENCE_HASH, APPROVED_CANDIDATE_ID),
        )
        assert cursor.rowcount == 1
    connection.commit()


def _candidate_state(
    connection: psycopg.Connection[dict[str, object]],
    candidate_id: str,
) -> tuple[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT lifecycle_status, review_posture
            FROM idea_candidate_record
            WHERE candidate_id = %s
            """,
            (candidate_id,),
        )
        row = cursor.fetchone()
    assert row is not None
    return str(row["lifecycle_status"]), str(row["review_posture"])


def _candidate_json_state(
    connection: psycopg.Connection[dict[str, object]],
    candidate_id: str,
) -> tuple[str, str, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                candidate_json ->> 'lifecycle_status' AS lifecycle_status,
                candidate_json ->> 'review_posture' AS review_posture,
                candidate_json -> 'suppression_reason' AS suppression_reason
            FROM idea_candidate_record
            WHERE candidate_id = %s
            """,
            (candidate_id,),
        )
        row = cursor.fetchone()
    assert row is not None
    return (
        str(row["lifecycle_status"]),
        str(row["review_posture"]),
        row["suppression_reason"],
    )


def _repair_audit_count(
    connection: psycopg.Connection[dict[str, object]],
    candidate_id: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM idea_audit_event
            WHERE candidate_id = %s
              AND event_type = 'idea.migration.superseded_approval_reopened.v1'
            """,
            (candidate_id,),
        )
        row = cursor.fetchone()
    assert row is not None
    return cast(int, row["row_count"])


def _repair_transition_count(
    connection: psycopg.Connection[dict[str, object]],
    candidate_id: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM idea_lifecycle_history
            WHERE candidate_id = %s
              AND actor_subject = 'lotus-idea-migration-032'
              AND source_status = 'approved'
              AND target_status = 'ready_for_review'
            """,
            (candidate_id,),
        )
        row = cursor.fetchone()
    assert row is not None
    return cast(int, row["row_count"])


def _migration() -> MigrationStep:
    return next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "032"
    )
