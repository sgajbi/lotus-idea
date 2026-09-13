from __future__ import annotations

import psycopg

from app.main import app
from tests.integration.postgres_runtime_support import high_cash_payload, persistence_headers
from tests.support.http import managed_test_client


def test_postgres_presentation_receipt_requires_complete_scope_before_durable_write(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-presentation-receipt-scope-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])

    queue = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=_scoped_headers("idea.review.queue.read"),
    )
    assert queue.status_code == 200
    item = queue.json()["items"][0]
    candidate = item["candidate"]
    assert candidate["candidateId"] == candidate_id
    payload = {
        "tenantId": "tenant-private-bank-sg",
        "presentedAtUtc": "2026-06-21T10:14:00Z",
        "rankAtPresentation": item["rank"],
        "visibleCandidateCount": len(queue.json()["items"]),
        "queueSnapshotDigest": f"sha256:{'a' * 64}",
        "queuePolicyVersion": queue.json()["policyVersion"],
        "rankingPolicyVersion": item["policyVersion"],
        "candidateMaterialVersion": candidate["materialVersion"],
        "candidateEvidenceVersion": candidate["evidenceVersion"],
        "sourceRevisionVectorDigest": candidate["sourceRevisionVectorDigest"],
        "sourceCutPosture": candidate["sourceCutPosture"],
    }
    route = f"/api/v1/idea-candidates/{candidate_id}/presentation-receipts"

    incomplete_headers = _record_headers("receipt-postgres-scope-001")
    incomplete_headers.pop("X-Caller-Client-Ids")
    incomplete_refusal = client.post(route, json=payload, headers=incomplete_headers)
    mismatched_headers = _record_headers("receipt-postgres-scope-001")
    mismatched_headers["X-Caller-Portfolio-Ids"] = "portfolio-other"
    mismatched_refusal = client.post(route, json=payload, headers=mismatched_headers)

    assert incomplete_refusal.status_code == 403
    assert incomplete_refusal.json()["code"] == "permission_denied"
    assert mismatched_refusal.status_code == 403
    assert mismatched_refusal.json()["code"] == "permission_denied"
    assert candidate_id not in incomplete_refusal.text
    assert _receipt_count(postgres_database_url) == 0

    accepted = client.post(
        route, json=payload, headers=_record_headers("receipt-postgres-scope-001")
    )
    replayed = client.post(
        route, json=payload, headers=_record_headers("receipt-postgres-scope-001")
    )

    assert accepted.status_code == 201
    assert replayed.status_code == 200
    assert replayed.json()["receipt"] == accepted.json()["receipt"]
    assert _receipt_count(postgres_database_url) == 1


def _scoped_headers(capability: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capability,
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
    }


def _record_headers(idempotency_key: str) -> dict[str, str]:
    headers = _scoped_headers("idea.presentation-receipt.record")
    headers["X-Caller-Subject"] = "workbench-visible-render-producer"
    headers["Idempotency-Key"] = idempotency_key
    return headers


def _receipt_count(database_url: str) -> int:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM idea_candidate_presentation_receipt")
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])
