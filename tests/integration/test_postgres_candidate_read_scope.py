from __future__ import annotations

import psycopg
from tests.integration.postgres_runtime_support import high_cash_payload, persistence_headers
from tests.support.http import managed_test_client

from app.main import app


def test_postgres_candidate_reads_require_complete_scope_before_returning_durable_rows(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-candidate-read-scope-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    persisted_candidate_count = _candidate_count(postgres_database_url)

    incomplete_queue_headers = _read_headers("idea.review.queue.read")
    incomplete_queue_headers.pop("X-Caller-Client-Ids")
    queue_refusal = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=incomplete_queue_headers,
    )
    incomplete_detail_headers = _read_headers("idea.candidate.detail.read")
    incomplete_detail_headers.pop("X-Caller-Portfolio-Ids")
    detail_refusal = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=incomplete_detail_headers,
    )

    assert queue_refusal.status_code == 403
    assert queue_refusal.json()["code"] == "permission_denied"
    assert detail_refusal.status_code == 403
    assert detail_refusal.json()["code"] == "permission_denied"
    assert candidate_id not in queue_refusal.text
    assert candidate_id not in detail_refusal.text
    assert _candidate_count(postgres_database_url) == persisted_candidate_count

    authorized_queue = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=_read_headers("idea.review.queue.read"),
    )
    authorized_detail = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=_read_headers("idea.candidate.detail.read"),
    )

    assert authorized_queue.status_code == 200
    assert [item["candidate"]["candidateId"] for item in authorized_queue.json()["items"]] == [
        candidate_id
    ]
    assert authorized_detail.status_code == 200
    assert authorized_detail.json()["candidate"]["candidateId"] == candidate_id


def _read_headers(capability: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capability,
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
    }


def _candidate_count(database_url: str) -> int:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM idea_candidate_record")
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])
