from __future__ import annotations

from typing import cast

import psycopg
from psycopg.rows import dict_row

from app.domain import ReviewChannel
from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    MigrationExecutionPlan,
    build_migration_plan,
    execute_migration_plan,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_protocols import PostgresConnection
from scripts.seed_postgres_disaster_recovery_fixture import seed_disaster_recovery_fixture
from tests.integration.postgres_runtime_support import MIGRATIONS_DIR


def test_exact_review_authority_migration_quarantines_ambiguous_legacy_history(
    postgres_database_url: str,
) -> None:
    seed_disaster_recovery_fixture(
        postgres_database_url,
        confirm_disposable_database=True,
    )
    migration = next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "025"
    )
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        typed_connection = cast(MigrationConnection, connection)
        execute_migration_plan(typed_connection, rollback)
        _make_conversion_history_legacy(connection)
        execute_migration_plan(typed_connection, apply)

        findings = _audit_findings(connection)
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        record = repository.candidate_record_by_id("idea_dr_fixture_conversion")
        intent = repository.conversion_intent_by_id("dr-fixture-conversion-intent-001")

    assert findings == {
        "approved_candidate_without_exact_review_authority",
        "conversion_intent_without_exact_review_authority",
        "legacy_review_authority_unverified",
    }
    assert record is not None
    assert record.review_decisions[-1].review_channel is ReviewChannel.LEGACY_UNVERIFIED
    assert record.review_decisions[-1].authority_grant is None
    assert intent is not None
    assert intent.review_authority_grant is None


def _make_conversion_history_legacy(
    connection: psycopg.Connection[dict[str, object]],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE idea_review_decision
            SET decision_json = decision_json
                - 'candidate_material_version'
                - 'candidate_evidence_version'
                - 'review_channel'
                - 'presentation_receipt_id'
                - 'queue_snapshot_digest'
                - 'review_policy_version'
                - 'review_authority_policy_version'
            WHERE review_decision_id = 'dr-fixture-conversion-review-001'
            """
        )
        cursor.execute(
            """
            UPDATE idea_conversion_intent
            SET intent_json = intent_json #- '{review_authority_grant,authority_policy_version}'
            WHERE conversion_intent_id = 'dr-fixture-conversion-intent-001'
            """
        )
    connection.commit()


def _audit_findings(
    connection: psycopg.Connection[dict[str, object]],
) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT finding
            FROM idea_review_authority_migration_audit
            WHERE candidate_id = 'idea_dr_fixture_conversion'
            """
        )
        return {str(row["finding"]) for row in cursor.fetchall()}
