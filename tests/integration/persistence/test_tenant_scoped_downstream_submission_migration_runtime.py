from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionIdentityVersion,
    DownstreamSubmissionResourceType,
    SourceSystem,
    create_downstream_submission_claim,
)
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


RECORDED_AT = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


def test_tenant_scope_migration_attributes_legacy_claim_without_rewriting_reference(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        seed_active_conversion_resource(postgres_database_url, "conversion-legacy-scope-001")
        legacy_reference = _insert_legacy_claim(connection)

        execute_migration_plan(cast(MigrationConnection, connection), apply)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tenant_id, identity_version, support_reference
                FROM idea_downstream_submission
                WHERE idempotency_key = 'legacy-shared-key'
                """
            )
            row = cursor.fetchone()
        assert row == {
            "tenant_id": "tenant-private-bank-sg",
            "identity_version": "legacy_unscoped_v1",
            "support_reference": legacy_reference,
        }
        persisted = PostgresIdeaRepository(
            cast(PostgresConnection, connection)
        ).downstream_submission_by_idempotency_key("tenant-private-bank-sg", "legacy-shared-key")

    assert persisted is not None
    assert persisted.identity_version is DownstreamSubmissionIdentityVersion.LEGACY_UNSCOPED_V1
    assert persisted.support_reference == legacy_reference


def test_tenant_scope_migration_refuses_lossy_rollback_after_v2_claim(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    seed_active_conversion_resource(postgres_database_url, "conversion-v2-scope-001")
    claim = create_downstream_submission_claim(
        tenant_id="tenant-private-bank-sg",
        idempotency_key="v2-shared-key",
        request_fingerprint="sha256:c9191c49dd722105c1f2263dbab92526079963fe9398f44e9ee138d859403afd",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-v2-scope-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject="downstream-submission",
        claimed_at_utc=RECORDED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="downstream-attempt-v2-shared-key",
        lease_expires_at_utc=RECORDED_AT + timedelta(minutes=5),
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.claim_downstream_submission(claim)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="unsafe downgrade: tenant-scoped downstream submission identities exist",
        ):
            execute_migration_plan(cast(MigrationConnection, connection), rollback)

        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM idea_downstream_submission WHERE support_reference = %s",
                (claim.support_reference,),
            )
        connection.commit()


def test_tenant_scope_migration_refuses_contradictory_candidate_scope(
    postgres_database_url: str,
) -> None:
    migration = _migration()
    rollback = MigrationExecutionPlan(MigrationDirection.ROLLBACK, (migration,))
    apply = MigrationExecutionPlan(MigrationDirection.APPLY, (migration,))
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback)
        candidate_id = seed_active_conversion_resource(
            postgres_database_url, "conversion-legacy-scope-001"
        )
        _insert_legacy_claim(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE idea_candidate_record
                SET candidate_json = jsonb_set(
                    candidate_json,
                    '{access_scope,tenant_id}',
                    '"tenant-contradiction"'::jsonb
                )
                WHERE candidate_id = %s
                """,
                (candidate_id,),
            )
        connection.commit()

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="cannot attribute every downstream submission",
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


def _migration() -> MigrationStep:
    return next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "027"
    )


def _insert_legacy_claim(
    connection: psycopg.Connection[dict[str, object]],
) -> str:
    legacy_reference = "downstream-submission-3a617b47b561ff92a6701c81"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_downstream_submission (
                idempotency_key, request_fingerprint, resource_type, resource_id,
                target, source_authority, status, downstream_failure_reason,
                correlation_id, trace_id, submitted_at_utc, support_reference,
                attempt_count, updated_at_utc, lease_owner, lease_attempt_id,
                lease_expires_at_utc, audit_json, owner_receipt_json
            ) VALUES (
                'legacy-shared-key', 'sha256:484ad9236fd6d1bf3c6e49f5d6b167795f3599aeeb2903edcde089c54460cbe9', 'conversion_intent',
                'conversion-legacy-scope-001', 'advise_proposal', 'lotus-advise',
                'in_flight', NULL, 'corr-legacy', 'trace-legacy', %s, %s, 1, %s,
                'downstream-submission', 'downstream-attempt-legacy-shared-key', %s,
                jsonb_build_array(jsonb_build_object(
                    'auditId', 'downstream-audit-legacy-shared-key',
                    'action', 'claimed',
                    'actorSubject', 'downstream-submission',
                    'previousPosture', NULL,
                    'currentPosture', 'in_flight',
                    'occurredAtUtc', %s::text,
                    'reason', NULL,
                    'changeReference', NULL
                )),
                NULL
            )
            """,
            (
                RECORDED_AT,
                legacy_reference,
                RECORDED_AT,
                RECORDED_AT + timedelta(minutes=5),
                RECORDED_AT.isoformat(),
            ),
        )
    connection.commit()
    return legacy_reference
