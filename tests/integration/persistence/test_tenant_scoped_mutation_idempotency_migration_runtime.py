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
from tests.integration.postgres_runtime_support import (
    MIGRATIONS_DIR,
    seed_active_conversion_resource,
)


RECORDED_AT = datetime(2026, 9, 7, 8, 0, tzinfo=UTC)


def test_migration_backfills_candidate_tenant_and_preserves_raw_key(
    postgres_database_url: str,
) -> None:
    rollback = _rollback_plan()
    apply = _apply_plan()
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        candidate_id = seed_active_conversion_resource(
            postgres_database_url,
            "conversion-idempotency-backfill",
            tenant_id="tenant-private-bank-sg",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idea_idempotency_record (
                    idempotency_key, operation_name, payload_hash, candidate_id, created_at_utc
                ) VALUES ('legacy-client-key', 'candidate', 'sha256:legacy', %s, %s)
                """,
                (candidate_id, RECORDED_AT),
            )
        connection.commit()

        execute_migration_plan(cast(MigrationConnection, connection), apply)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tenant_id, idempotency_key, candidate_id
                FROM idea_idempotency_record
                WHERE idempotency_key = 'legacy-client-key'
                """
            )
            assert cursor.fetchone() == {
                "tenant_id": "tenant-private-bank-sg",
                "idempotency_key": "legacy-client-key",
                "candidate_id": candidate_id,
            }


def test_migration_refuses_unscoped_candidate_history(
    postgres_database_url: str,
) -> None:
    rollback = _rollback_plan()
    apply = _apply_plan()
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        candidate_id = seed_active_conversion_resource(
            postgres_database_url,
            "conversion-idempotency-unscoped",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE idea_candidate_record
                SET candidate_json = candidate_json #- '{access_scope,tenant_id}'
                WHERE candidate_id = %s
                """,
                (candidate_id,),
            )
            cursor.execute(
                """
                INSERT INTO idea_idempotency_record (
                    idempotency_key, operation_name, payload_hash, candidate_id, created_at_utc
                ) VALUES ('unscoped-client-key', 'candidate', 'sha256:unscoped', %s, %s)
                """,
                (candidate_id, RECORDED_AT),
            )
        connection.commit()

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="candidate-bound idempotency rows require a source candidate tenant",
        ):
            execute_migration_plan(cast(MigrationConnection, connection), apply)

        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE idea_candidate_record
                SET candidate_json = jsonb_set(
                    candidate_json,
                    '{access_scope,tenant_id}',
                    '"tenant-private-bank-sg"'::jsonb
                )
                WHERE candidate_id = %s
                """,
                (candidate_id,),
            )
        connection.commit()
        execute_migration_plan(cast(MigrationConnection, connection), apply)


def test_migration_refuses_lossy_rollback_after_cross_tenant_key_reuse(
    postgres_database_url: str,
) -> None:
    rollback = _rollback_plan()
    candidate_a = seed_active_conversion_resource(
        postgres_database_url,
        "conversion-idempotency-tenant-a",
        tenant_id="tenant-a",
    )
    candidate_b = seed_active_conversion_resource(
        postgres_database_url,
        "conversion-idempotency-tenant-b",
        tenant_id="tenant-b",
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO idea_idempotency_record (
                    tenant_id, idempotency_key, operation_name, payload_hash,
                    candidate_id, created_at_utc
                ) VALUES (%s, 'shared-client-key', 'candidate', %s, %s, %s)
                """,
                (
                    ("tenant-a", "sha256:a", candidate_a, RECORDED_AT),
                    ("tenant-b", "sha256:b", candidate_b, RECORDED_AT),
                ),
            )
        connection.commit()

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="cannot roll back tenant-scoped idempotency while duplicate raw keys exist",
        ):
            execute_migration_plan(cast(MigrationConnection, connection), rollback)

        connection.rollback()


def _scoped_migrations() -> tuple[MigrationStep, ...]:
    return tuple(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version in {"028", "030"}
    )


def _apply_plan() -> MigrationExecutionPlan:
    return MigrationExecutionPlan(MigrationDirection.APPLY, _scoped_migrations())


def _rollback_plan() -> MigrationExecutionPlan:
    return MigrationExecutionPlan(
        MigrationDirection.ROLLBACK,
        tuple(reversed(_scoped_migrations())),
    )
