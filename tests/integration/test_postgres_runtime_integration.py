from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator, cast

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.repository_state import reset_idea_repository_for_tests
from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    build_migration_plan,
    execute_migration_plan,
)
from app.main import app


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "migrations"
POSTGRES_URL_ENV = "LOTUS_IDEA_POSTGRES_INTEGRATION_URL"
POSTGRES_REQUIRED_ENV = "LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED"


@pytest.fixture
def postgres_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    database_url = os.getenv(POSTGRES_URL_ENV, "").strip()
    if not database_url:
        if os.getenv(POSTGRES_REQUIRED_ENV) == "1":
            pytest.fail(f"{POSTGRES_URL_ENV} is required for PostgreSQL integration proof")
        pytest.skip(f"{POSTGRES_URL_ENV} is not configured")

    _execute_migrations(database_url, MigrationDirection.ROLLBACK)
    _execute_migrations(database_url, MigrationDirection.APPLY)
    monkeypatch.setenv("LOTUS_IDEA_DATABASE_URL", database_url)
    reset_idea_repository_for_tests(reload_from_environment=True)
    try:
        yield database_url
    finally:
        reset_idea_repository_for_tests()
        _execute_migrations(database_url, MigrationDirection.ROLLBACK)


def test_postgres_runtime_provider_persists_api_state_across_reloaded_connections(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    headers = _persistence_headers("postgres-runtime-proof-high-cash-001")
    payload = _high_cash_payload()

    accepted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=headers,
    )
    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=headers,
    )

    assert accepted.status_code == 200
    assert replayed.status_code == 200
    accepted_payload = accepted.json()
    replayed_payload = replayed.json()
    assert accepted_payload["durableStorageBacked"] is True
    assert replayed_payload["durableStorageBacked"] is True
    assert accepted_payload["persistence"]["decision"] == "accepted"
    assert replayed_payload["persistence"]["decision"] == "replayed"
    assert (
        replayed_payload["persistence"]["candidateId"]
        == accepted_payload["persistence"]["candidateId"]
    )
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1


def _execute_migrations(database_url: str, direction: MigrationDirection) -> None:
    plan = build_migration_plan(MIGRATIONS_DIR, direction)
    with psycopg.connect(database_url) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), plan)


def _table_count(database_url: str, table_name: str) -> int:
    allowed_tables = {"idea_candidate_record", "idea_idempotency_record"}
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported test table: {table_name}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


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


def _high_cash_payload() -> dict[str, Any]:
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
    }


def _persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-postgres-runtime-proof",
        "Idempotency-Key": idempotency_key,
    }
