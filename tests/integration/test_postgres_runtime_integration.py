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
POSTGRES_SCHEMA_TABLES = (
    "idea_candidate_record",
    "idea_idempotency_record",
    "idea_lifecycle_history",
    "idea_audit_event",
    "idea_review_decision",
    "idea_feedback_event",
    "idea_conversion_intent",
    "idea_conversion_outcome",
    "idea_report_evidence_pack_request",
)


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


def test_postgres_migration_rollback_and_reapply_restores_runtime_contract(
    postgres_database_url: str,
) -> None:
    assert _schema_tables_exist(postgres_database_url) is True

    _execute_migrations(postgres_database_url, MigrationDirection.ROLLBACK)
    assert _schema_tables_exist(postgres_database_url) is False

    _execute_migrations(postgres_database_url, MigrationDirection.APPLY)
    assert _schema_tables_exist(postgres_database_url) is True

    reset_idea_repository_for_tests(reload_from_environment=True)
    client = TestClient(app)
    recovered = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(),
        headers=_persistence_headers("postgres-runtime-proof-recovery-001"),
    )

    assert recovered.status_code == 200
    recovered_payload = recovered.json()
    assert recovered_payload["durableStorageBacked"] is True
    assert recovered_payload["persistence"]["decision"] == "accepted"
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1


def test_postgres_runtime_provider_persists_review_conversion_and_report_workflow(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persist_headers = _persistence_headers("postgres-runtime-proof-workflow-persist-001")
    high_cash_payload = _high_cash_payload()

    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload,
        headers=persist_headers,
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])

    reset_idea_repository_for_tests(reload_from_environment=True)
    queue = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:10:00Z"},
        headers=_review_queue_headers(),
    )
    assert queue.status_code == 200
    queue_payload = queue.json()
    assert queue_payload["durableStorageBacked"] is True
    assert queue_payload["items"][0]["candidate"]["candidateId"] == candidate_id

    _transition_candidate_to_review_ready(client, candidate_id)
    review_headers = _review_headers("postgres-runtime-proof-review-approve-001")
    review_payload = _approve_review_payload()
    review = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=review_payload,
        headers=review_headers,
    )
    assert review.status_code == 200
    review_payload_response = review.json()
    assert review_payload_response["durableStorageBacked"] is True
    assert review_payload_response["persistence"]["decision"] == "accepted"
    assert review_payload_response["persistence"]["lifecycleStatus"] == "approved"
    assert review_payload_response["persistence"]["reviewPosture"] == "approved_for_conversion"

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_review = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=review_payload,
        headers=review_headers,
    )
    assert replayed_review.status_code == 200
    assert replayed_review.json()["durableStorageBacked"] is True
    assert replayed_review.json()["persistence"]["decision"] == "replayed"

    feedback = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=_feedback_payload(),
        headers=_feedback_headers("postgres-runtime-proof-feedback-001"),
    )
    assert feedback.status_code == 200
    assert feedback.json()["durableStorageBacked"] is True
    assert feedback.json()["persistence"]["decision"] == "accepted"

    reset_idea_repository_for_tests(reload_from_environment=True)
    conversion_headers = _conversion_intent_headers("postgres-runtime-proof-conversion-intent-001")
    conversion_payload = _conversion_intent_payload()
    conversion = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_payload,
        headers=conversion_headers,
    )
    assert conversion.status_code == 200
    conversion_response = conversion.json()
    assert conversion_response["durableStorageBacked"] is True
    assert conversion_response["persistence"]["decision"] == "accepted"
    assert conversion_response["persistence"]["lifecycleStatus"] == "converted_to_report"

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_conversion = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_payload,
        headers=conversion_headers,
    )
    assert replayed_conversion.status_code == 200
    assert replayed_conversion.json()["durableStorageBacked"] is True
    assert replayed_conversion.json()["persistence"]["decision"] == "replayed"

    outcome = client.post(
        "/api/v1/conversion-intents/conversion-report-001/outcomes",
        json=_conversion_outcome_payload(),
        headers=_conversion_outcome_headers("postgres-runtime-proof-conversion-outcome-001"),
    )
    assert outcome.status_code == 200
    assert outcome.json()["durableStorageBacked"] is True
    assert outcome.json()["persistence"]["decision"] == "accepted"

    reset_idea_repository_for_tests(reload_from_environment=True)
    report_headers = _report_evidence_pack_headers(
        "postgres-runtime-proof-report-evidence-pack-001"
    )
    report_payload = _report_evidence_pack_payload()
    report_pack = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=report_payload,
        headers=report_headers,
    )
    assert report_pack.status_code == 200
    report_response = report_pack.json()
    assert report_response["durableStorageBacked"] is True
    assert report_response["persistence"]["decision"] == "accepted"
    assert report_response["reportEvidencePack"]["candidateId"] == candidate_id
    assert report_response["reportEvidencePack"]["createsRenderedOutput"] is False
    assert report_response["reportEvidencePack"]["createsArchiveRecord"] is False

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_report_pack = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=report_payload,
        headers=report_headers,
    )
    assert replayed_report_pack.status_code == 200
    assert replayed_report_pack.json()["durableStorageBacked"] is True
    assert replayed_report_pack.json()["persistence"]["decision"] == "replayed"

    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_review_decision") == 1
    assert _table_count(postgres_database_url, "idea_feedback_event") == 1
    assert _table_count(postgres_database_url, "idea_conversion_intent") == 1
    assert _table_count(postgres_database_url, "idea_conversion_outcome") == 1
    assert _table_count(postgres_database_url, "idea_report_evidence_pack_request") == 1


def _execute_migrations(database_url: str, direction: MigrationDirection) -> None:
    plan = build_migration_plan(MIGRATIONS_DIR, direction)
    with psycopg.connect(database_url) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), plan)


def _table_count(database_url: str, table_name: str) -> int:
    if table_name not in POSTGRES_SCHEMA_TABLES:
        raise ValueError(f"Unsupported test table: {table_name}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


def _schema_tables_exist(database_url: str) -> bool:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(POSTGRES_SCHEMA_TABLES),),
            )
            existing_tables = {str(row[0]) for row in cursor.fetchall()}
    return existing_tables == set(POSTGRES_SCHEMA_TABLES)


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


def _review_queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-postgres-runtime-proof-queue",
    }


def _lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "X-Correlation-Id": "corr-postgres-runtime-proof-lifecycle",
        "Idempotency-Key": idempotency_key,
    }


def _review_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-review",
        "Idempotency-Key": idempotency_key,
    }


def _feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-feedback",
        "Idempotency-Key": idempotency_key,
    }


def _conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-intent",
        "Idempotency-Key": idempotency_key,
    }


def _conversion_outcome_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": "idea.conversion.outcome.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-outcome",
        "Idempotency-Key": idempotency_key,
    }


def _report_evidence_pack_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
        "X-Correlation-Id": "corr-postgres-runtime-proof-report-pack",
        "Idempotency-Key": idempotency_key,
    }


def _access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }


def _authorized_scope() -> dict[str, list[str]]:
    return {
        "tenantIds": ["tenant-private-bank-sg"],
        "bookIds": ["book-advisor-001"],
        "portfolioIds": ["PB_SG_GLOBAL_BAL_001"],
        "clientIds": ["client-001"],
    }


def _lifecycle_payload(
    *,
    transition_id: str,
    target_status: str,
    changed_at_utc: str,
) -> dict[str, Any]:
    return {
        "transitionId": transition_id,
        "targetLifecycleStatus": target_status,
        "changedAtUtc": changed_at_utc,
        "reasonCodes": ["review_required"],
    }


def _approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "review-approve-001",
        "action": "approve_for_conversion",
        "accessScope": _access_scope(),
        "authorizedScope": _authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def _feedback_payload() -> dict[str, Any]:
    return {
        "feedbackId": "feedback-useful-001",
        "accessScope": _access_scope(),
        "authorizedScope": _authorized_scope(),
        "outcome": "useful",
        "reasonCodes": ["review_required"],
        "recordedAtUtc": "2026-06-21T10:06:00Z",
    }


def _conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def _conversion_outcome_payload() -> dict[str, Any]:
    return {
        "conversionOutcomeId": "conversion-report-outcome-001",
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "downstreamReference": "report-evidence-pack-001",
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def _report_evidence_pack_payload() -> dict[str, Any]:
    return {
        "reportEvidencePackId": "report-evidence-pack-001",
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": False,
    }


def _transition_candidate_to_review_ready(client: TestClient, candidate_id: str) -> None:
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=_lifecycle_payload(
                transition_id=f"lifecycle-{target_status}-001",
                target_status=target_status,
                changed_at_utc=f"2026-06-21T10:{index:02d}:00Z",
            ),
            headers=_lifecycle_headers(f"postgres-runtime-proof-lifecycle-{target_status}-001"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["durableStorageBacked"] is True
        assert payload["persistence"]["decision"] == "accepted"
        assert payload["persistence"]["lifecycleStatus"] == target_status
        reset_idea_repository_for_tests(reload_from_environment=True)
