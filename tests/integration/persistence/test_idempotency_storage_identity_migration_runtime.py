from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import psycopg
from psycopg.rows import dict_row

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


RECORDED_AT = datetime(2026, 9, 8, 8, 0, tzinfo=UTC)


def test_migration_adds_storage_primary_key_without_changing_business_identity(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))
    candidate_a = seed_active_conversion_resource(
        postgres_database_url,
        "idempotency-storage-tenant-a",
        tenant_id="tenant-storage-a",
    )
    candidate_b = seed_active_conversion_resource(
        postgres_database_url,
        "idempotency-storage-tenant-b",
        tenant_id="tenant-storage-b",
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO idea_idempotency_record (
                    tenant_id, idempotency_key, operation_name, payload_hash,
                    candidate_id, created_at_utc
                ) VALUES (%s, 'shared-business-key', 'candidate', %s, %s, %s)
                """,
                (
                    (
                        "tenant-storage-a",
                        "sha256:4248d1d19d0ef82f520e2636c3ee71b1543b2650c50b5a78361288825b452b4a",
                        candidate_a,
                        RECORDED_AT,
                    ),
                    (
                        "tenant-storage-b",
                        "sha256:6ceabb5f768aab73f71ed2f5f378f0d4c5a2e21c2911e640b8c8e0940df92797",
                        candidate_b,
                        RECORDED_AT,
                    ),
                ),
            )
            cursor.execute(
                """
                INSERT INTO idea_idempotency_record (
                    tenant_id, idempotency_key, operation_name, payload_hash,
                    candidate_id, created_at_utc
                ) VALUES (
                    NULL, 'system-key', 'outbox_delivery_run', 'sha256:fc39bf37970d5c8b2be251a0ff1b42f87f2afafd39e0bef3442cd638c6c7ec0f', NULL, %s
                )
                """,
                (RECORDED_AT,),
            )
        connection.commit()

        execute_migration_plan(cast(MigrationConnection, connection), apply)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT idempotency_record_identity, tenant_id, idempotency_key
                FROM idea_idempotency_record
                WHERE idempotency_key = 'shared-business-key'
                ORDER BY tenant_id
                """
            )
            rows = cursor.fetchall()
            assert [row["tenant_id"] for row in rows] == [
                "tenant-storage-a",
                "tenant-storage-b",
            ]
            assert [row["idempotency_record_identity"] for row in rows] == [
                "tenant:16:tenant-storage-a:19:shared-business-key",
                "tenant:16:tenant-storage-b:19:shared-business-key",
            ]

            cursor.execute(
                """
                SELECT idempotency_record_identity
                FROM idea_idempotency_record
                WHERE idempotency_key = 'system-key'
                """
            )
            assert cursor.fetchone() == {"idempotency_record_identity": "system:10:system-key"}

            cursor.execute(
                """
                SELECT attribute.attname, attribute.attgenerated, class.relreplident
                FROM pg_constraint AS constraint_record
                JOIN pg_class AS class ON class.oid = constraint_record.conrelid
                JOIN unnest(constraint_record.conkey) WITH ORDINALITY AS key(attnum, position)
                  ON TRUE
                JOIN pg_attribute AS attribute
                  ON attribute.attrelid = class.oid AND attribute.attnum = key.attnum
                WHERE constraint_record.contype = 'p'
                  AND class.oid = 'idea_idempotency_record'::regclass
                ORDER BY key.position
                """
            )
            assert cursor.fetchall() == [
                {
                    "attname": "idempotency_record_identity",
                    "attgenerated": "s",
                    "relreplident": "d",
                }
            ]


def test_migration_rollback_removes_only_storage_identity(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'idea_idempotency_record'
                ORDER BY ordinal_position
                """
            )
            columns = {row["column_name"] for row in cursor.fetchall()}
            assert "idempotency_record_identity" not in columns
            assert {"tenant_id", "idempotency_key", "candidate_id"}.issubset(columns)

            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'idea_idempotency_record'
                """
            )
            indexes = {row["indexname"] for row in cursor.fetchall()}
            assert "uq_idea_idempotency_record_tenant_key" in indexes
            assert "uq_idea_idempotency_record_system_key" in indexes


def _migration() -> MigrationStep:
    return next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "030"
    )
