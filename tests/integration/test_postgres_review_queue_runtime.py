from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from tests.support.http import managed_test_client

from app.domain import (
    BondMaturitySignalInput,
    BondMaturitySignalPolicy,
    EvidenceFreshness,
    QueueExclusionReason,
    ReviewAccessScope,
    ReviewQueueAudience,
    SourceRef,
    SourceSystem,
    evaluate_bond_maturity_signal,
)
from app.main import app
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.runtime.repository_state import get_idea_repository


def test_postgres_review_queue_and_readiness_enforce_applicability_expiry_boundary(
    postgres_database_url: str,
) -> None:
    del postgres_database_url
    repository = cast(PostgresIdeaRepository, get_idea_repository())
    evaluation = evaluate_bond_maturity_signal(
        _bond_maturity_input(),
        BondMaturitySignalPolicy(
            policy_version="bond-maturity-review-v2",
            maturity_window_days=30,
        ),
    )
    assert evaluation.candidate is not None
    candidate = evaluation.candidate
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="postgres-bond-applicability-expiry",
        payload={"candidate_id": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    )
    assert persisted.record is not None
    rehydrated = repository.candidate_record_by_id(candidate.candidate_id)
    assert rehydrated is not None
    assert rehydrated.candidate.evidence_packet.applicability_expires_at_utc == datetime(
        2026, 6, 23, tzinfo=UTC
    )

    before = repository.review_queue_candidate_page(
        evaluated_at_utc=datetime(2026, 6, 22, 23, 59, 59, tzinfo=UTC),
        audience=ReviewQueueAudience.ADVISOR,
        expected_snapshot_token=None,
        queue_policy_version="idea-deterministic-ranking-v1",
        rankable_score_policy_versions=("bond-maturity-review-v2",),
        access_scope_filter=None,
        limit=10,
        offset=0,
    )
    exactly_at = repository.review_queue_candidate_page(
        evaluated_at_utc=datetime(2026, 6, 23, tzinfo=UTC),
        audience=ReviewQueueAudience.ADVISOR,
        expected_snapshot_token=None,
        queue_policy_version="idea-deterministic-ranking-v1",
        rankable_score_policy_versions=("bond-maturity-review-v2",),
        access_scope_filter=None,
        limit=10,
        offset=0,
    )
    readiness = repository.review_queue_readiness_summary(
        evaluated_at_utc=datetime(2026, 6, 23, tzinfo=UTC),
        audience=ReviewQueueAudience.ADVISOR,
        rankable_score_policy_versions=("bond-maturity-review-v2",),
        access_scope_filter=None,
    )

    assert [record.candidate.candidate_id for record in before.candidate_records] == [
        candidate.candidate_id
    ]
    assert exactly_at.candidate_records == ()
    assert exactly_at.total_excluded_candidate_count == 1
    assert readiness.reviewable_item_count == 0
    assert readiness.excluded_candidate_count == 1
    assert readiness.exclusion_counts[QueueExclusionReason.EXPIRED.value] == 1


def test_postgres_review_queue_honors_persisted_snooze_until_exact_boundary(
    postgres_database_url: str,
) -> None:
    del postgres_database_url
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(suffix=""),
        headers=_persistence_headers("postgres-review-queue-snooze-candidate"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    snoozed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json={
            "reviewId": "postgres-review-snooze-001",
            "action": "snooze",
            "reasonCodes": ["review_required"],
            "decidedAtUtc": "2026-06-21T10:05:00Z",
            "snoozedUntilUtc": "2026-06-21T11:00:00Z",
        },
        headers=_snooze_headers(),
    )
    assert snoozed.status_code == 200

    hidden = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:30:00Z", "limit": 10},
        headers=_review_queue_headers(),
    )
    assert hidden.status_code == 200
    assert hidden.json()["items"] == []
    assert hidden.json()["page"]["totalExcludedCandidateCount"] == 1

    awakened = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T11:00:00Z", "limit": 10},
        headers=_review_queue_headers(),
    )
    assert awakened.status_code == 200
    assert [item["candidate"]["candidateId"] for item in awakened.json()["items"]] == [candidate_id]


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


def _bond_maturity_input() -> BondMaturitySignalInput:
    as_of_date = date(2026, 6, 21)
    evaluated_at_utc = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    def source_ref(product_id: str) -> SourceRef:
        return SourceRef(
            product_id=product_id,
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route=f"/source/{product_id}",
            as_of_date=as_of_date,
            generated_at_utc=evaluated_at_utc,
            content_hash=f"sha256:{product_id}:applicability-expiry",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )

    return BondMaturitySignalInput(
        as_of_date=as_of_date,
        source_reported_next_maturity_date=date(2026, 6, 22),
        source_reported_maturing_position_count=2,
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
        maturity_fact_ref=source_ref("lotus-core:PortfolioMaturitySummary:v1"),
        evaluated_at_utc=evaluated_at_utc,
        access_scope=ReviewAccessScope(
            tenant_id="tenant-private-bank-sg",
            book_id="book-advisor-001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            client_id="client-001",
        ),
    )


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
            "portfolioId": f"PB_SG_GLOBAL_BAL_001{suffix}",
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


def _snooze_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-postgres-review-queue-snooze",
        "X-Trace-Id": "trace-postgres-review-queue-snooze",
        "Idempotency-Key": "postgres-review-queue-snooze-001",
    }
