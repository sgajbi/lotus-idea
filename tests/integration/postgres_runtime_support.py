from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import Any, Callable, TypeVar, cast

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    build_migration_plan,
    execute_migration_plan,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "migrations"
POSTGRES_URL_ENV = "LOTUS_IDEA_POSTGRES_INTEGRATION_URL"
POSTGRES_REQUIRED_ENV = "LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED"
_T = TypeVar("_T")


def execute_migrations(database_url: str, direction: MigrationDirection) -> None:
    plan = build_migration_plan(MIGRATIONS_DIR, direction)
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), plan)


def high_cash_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": _source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": _source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": _source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": _source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "entitlementAllowed": True,
        "accessScope": {
            "tenantId": "tenant-private-bank-sg",
            "bookId": "book-advisor-001",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
    }


def persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-postgres-runtime-proof",
        "X-Trace-Id": "trace-postgres-runtime-proof",
        "Idempotency-Key": idempotency_key,
    }


def seed_active_conversion_resource(database_url: str, conversion_intent_id: str) -> str:
    candidate_id = f"candidate-{conversion_intent_id}"
    recorded_at = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_candidate_record (
                candidate_id, family, lifecycle_status, review_posture,
                evidence_packet_id, evidence_hash, candidate_json,
                persisted_at_utc, updated_at_utc
            ) VALUES (%s, 'high_cash', 'approved', 'approved_for_conversion',
                      'evidence-runtime', 'sha256:runtime', %s, %s, %s)
            """,
            (
                candidate_id,
                Jsonb({"access_scope": {"tenant_id": "tenant-private-bank-sg"}}),
                recorded_at,
                recorded_at,
            ),
        )
        cursor.execute(
            """
            INSERT INTO idea_data_lifecycle_control (
                candidate_id, tenant_id, policy_ref, state,
                retention_expires_at_utc, version, updated_at_utc
            ) VALUES (%s, 'tenant-private-bank-sg',
                      'lotus-idea:regulated-advisory-evidence:seven-year:v1',
                      'active', %s, 1, %s)
            """,
            (candidate_id, recorded_at + timedelta(days=365 * 7), recorded_at),
        )
        cursor.execute(
            """
            INSERT INTO idea_conversion_intent (
                conversion_intent_id, candidate_id, target, actor_subject,
                intent_json, requested_at_utc
            ) VALUES (%s, %s, 'advise_proposal', 'advisor-redacted', '{}'::jsonb, %s)
            """,
            (conversion_intent_id, candidate_id, recorded_at),
        )
    return candidate_id


def run_concurrent_repository_mutations(
    database_url: str,
    mutation: Callable[[PostgresIdeaRepository, str], _T],
    idempotency_keys: tuple[str, str],
) -> tuple[_T, _T]:
    barrier = Barrier(2)

    def run(idempotency_key: str) -> _T:
        with psycopg.connect(database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(Any, connection))
            barrier.wait(timeout=10)
            return mutation(repository, idempotency_key)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(run, key) for key in idempotency_keys)
        return cast(
            tuple[_T, _T],
            tuple(future.result(timeout=20) for future in futures),
        )


def _source_ref(product_id: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
