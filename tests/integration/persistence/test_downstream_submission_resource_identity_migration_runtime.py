from __future__ import annotations

from datetime import UTC, datetime
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
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_protocols import PostgresConnection
from tests.integration.postgres_runtime_support import (
    MIGRATIONS_DIR,
    seed_active_conversion_resource,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim


RECORDED_AT = datetime(2026, 9, 9, 8, 0, tzinfo=UTC)


def test_resource_identity_migration_refuses_duplicates_and_rollback_restores_prior_index(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))
    resource_id = "conversion-migration-resource-identity"

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        seed_active_conversion_resource(postgres_database_url, resource_id)
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.claim_downstream_submission(
            build_downstream_submission_claim(
                idempotency_key="migration-resource-key-one",
                request_fingerprint=(
                    "sha256:3e9e64e859c4c1cccf6d6790c0353319bc16be88ea78bb09e63e1480c1b6acda"
                ),
                resource_id=resource_id,
                submitted_at_utc=RECORDED_AT,
            )
        )
        _clone_submission_with_new_transport_identity(connection)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="cannot enforce downstream submission resource identity",
        ):
            execute_migration_plan(cast(MigrationConnection, connection), apply)
        connection.rollback()

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM idea_downstream_submission WHERE idempotency_key = %s",
                ("migration-resource-key-two",),
            )
        connection.commit()
        execute_migration_plan(cast(MigrationConnection, connection), apply)

        with pytest.raises(psycopg.errors.UniqueViolation):
            _clone_submission_with_new_transport_identity(connection)
        connection.rollback()

        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        _clone_submission_with_new_transport_identity(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'idea_downstream_submission'
                """
            )
            indexes = {row["indexname"] for row in cursor.fetchall()}
        assert "uq_idea_downstream_submission_resource_identity" not in indexes
        assert "idx_idea_downstream_submission_resource" in indexes

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM idea_downstream_submission WHERE idempotency_key = %s",
                ("migration-resource-key-two",),
            )
        connection.commit()
        execute_migration_plan(cast(MigrationConnection, connection), apply)


def _clone_submission_with_new_transport_identity(
    connection: psycopg.Connection[dict[str, object]],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_downstream_submission (
                tenant_id, identity_version, idempotency_key, request_fingerprint,
                resource_type, resource_id, target, source_authority, status,
                downstream_failure_reason, correlation_id, trace_id, submitted_at_utc,
                support_reference, attempt_count, updated_at_utc, lease_owner,
                lease_attempt_id, lease_expires_at_utc, audit_json, owner_receipt_json
            )
            SELECT
                tenant_id, identity_version, 'migration-resource-key-two',
                'sha256:79c82be96713903078b4d2fe8999ff28c9f73fa6a3b19b99663ea3cf249c9d7d',
                resource_type, resource_id, target, source_authority, status,
                downstream_failure_reason, correlation_id, trace_id, submitted_at_utc,
                'downstream-submission-aaaaaaaaaaaaaaaaaaaaaaaa', attempt_count,
                updated_at_utc, lease_owner, 'migration-resource-attempt-two',
                lease_expires_at_utc, audit_json, owner_receipt_json
            FROM idea_downstream_submission
            WHERE idempotency_key = 'migration-resource-key-one'
            """
        )
    connection.commit()


def _migration() -> MigrationStep:
    return next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "031"
    )
