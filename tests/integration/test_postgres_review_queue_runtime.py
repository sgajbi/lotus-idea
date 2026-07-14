from __future__ import annotations

from typing import Any

from tests.support.http import managed_test_client

from app.main import app


def test_postgres_review_queue_preserves_snapshot_across_future_insert_and_rejects_stale_token(
    postgres_database_url: str,
) -> None:
    del postgres_database_url
    client = managed_test_client(app)
    visible_candidate_ids = []
    for index in range(2):
        persisted = client.post(
            "/api/v1/idea-signals/high-cash/evaluate-and-persist",
            json=_high_cash_payload(suffix=f"-snapshot-visible-{index}"),
            headers=_persistence_headers(f"postgres-review-queue-snapshot-visible-{index}"),
        )
        assert persisted.status_code == 200
        visible_candidate_ids.append(str(persisted.json()["persistence"]["candidateId"]))

    first_page = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:10:00Z", "limit": 1},
        headers=_review_queue_headers(),
    )
    assert first_page.status_code == 200
    snapshot_token = str(first_page.json()["page"]["snapshotToken"])

    future = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(
            suffix="-snapshot-future",
            evaluated_at_utc="2026-06-21T10:11:00Z",
        ),
        headers=_persistence_headers("postgres-review-queue-snapshot-future"),
    )
    assert future.status_code == 200
    future_candidate_id = str(future.json()["persistence"]["candidateId"])

    second_page = client.get(
        "/api/v1/review-queues/advisor",
        params={
            "evaluatedAtUtc": "2026-06-21T10:10:00Z",
            "limit": 1,
            "offset": 1,
            "snapshotToken": snapshot_token,
        },
        headers=_review_queue_headers(),
    )
    assert second_page.status_code == 200
    assert second_page.json()["page"]["totalReviewableItemCount"] == 2
    returned_id = second_page.json()["items"][0]["candidate"]["candidateId"]
    assert returned_id == sorted(visible_candidate_ids)[1]
    assert returned_id != future_candidate_id

    backdated = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(suffix="-snapshot-backdated"),
        headers=_persistence_headers("postgres-review-queue-snapshot-backdated"),
    )
    assert backdated.status_code == 200
    stale_page = client.get(
        "/api/v1/review-queues/advisor",
        params={
            "evaluatedAtUtc": "2026-06-21T10:10:00Z",
            "limit": 1,
            "offset": 1,
            "snapshotToken": snapshot_token,
        },
        headers=_review_queue_headers(),
    )
    assert stale_page.status_code == 409
    assert stale_page.json()["code"] == "review_queue_snapshot_conflict"


def _source_ref(product_id: str, *, suffix: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}{suffix}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def _high_cash_payload(
    *,
    suffix: str,
    evaluated_at_utc: str = "2026-06-21T10:00:00Z",
) -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": evaluated_at_utc,
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": _source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix=suffix),
            "holdingsRef": _source_ref("lotus-core:HoldingsAsOf:v1", suffix=suffix),
            "cashMovementRef": _source_ref(
                "lotus-core:PortfolioCashMovementSummary:v1", suffix=suffix
            ),
            "cashflowProjectionRef": _source_ref(
                "lotus-core:PortfolioCashflowProjection:v1", suffix=suffix
            ),
        },
        "entitlementAllowed": True,
        "accessScope": {
            "tenantId": "tenant-private-bank-sg",
            "bookId": "book-advisor-001",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
    }


def _persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-postgres-review-queue-snapshot",
        "X-Trace-Id": "trace-postgres-review-queue-snapshot",
        "Idempotency-Key": idempotency_key,
    }


def _review_queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-postgres-review-queue-snapshot-read",
    }
