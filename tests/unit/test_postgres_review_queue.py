from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from app.domain import (
    EvidenceSupportability,
    IdeaCandidate,
    IdeaLifecycleStatus,
    QueueAccessScopeFilter,
    ReviewQueueSnapshotConflictError,
    ReviewAccessScope,
    ReviewPosture,
    UnsupportedEvidenceReason,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_review_queue import (
    REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS,
    _review_queue_candidate_predicates,
    load_review_queue_candidate_page,
    load_review_queue_readiness_summary,
)
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    high_cash_candidate,
)


QUEUE_EVALUATED_AT = EVALUATED_AT + timedelta(days=1)
QUEUE_POLICY_VERSION = "idea-deterministic-ranking-v1"


def test_postgres_repository_review_queue_page_uses_bounded_candidate_projection() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    in_scope_candidates = [
        queue_candidate(index=index, candidate_scope=access_scope()) for index in range(3)
    ]
    out_of_scope = queue_candidate(
        index=99,
        candidate_scope=ReviewAccessScope(
            tenant_id="tenant-001",
            book_id="book-001",
            portfolio_id="portfolio-out-of-scope",
            client_id="client-001",
        ),
    )
    for candidate in (*in_scope_candidates, out_of_scope):
        repository.persist_candidate(
            candidate,
            idempotency_key=f"signal-ingestion:high-cash:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
    assert connection.rows["idea_outbox_event"]
    connection.executed_sql.clear()

    page = PostgresIdeaRepository(connection).review_queue_candidate_page(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=QueueAccessScopeFilter(portfolio_id="portfolio-001"),
        limit=2,
        offset=1,
    )

    assert [record.candidate.candidate_id for record in page.candidate_records] == [
        "idea_queue_001",
        "idea_queue_002",
    ]
    assert page.total_reviewable_item_count == 3
    assert page.total_excluded_candidate_count == 1
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea review-queue-count */" in executed_sql
    assert "/* lotus-idea review-queue-page */" in executed_sql
    assert "limit %s offset %s" in executed_sql
    assert "idea_candidate_record" in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql
    assert "idea_report_evidence_pack_request" not in executed_sql
    assert "idea_ai_explanation_lineage" not in executed_sql


def test_postgres_review_queue_rejects_stale_token_after_backdated_insert() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    for index in (0, 1):
        candidate = queue_candidate(index=index, candidate_scope=access_scope())
        repository.persist_candidate(
            candidate,
            idempotency_key=f"signal-ingestion:high-cash:snapshot-{index}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
    evaluated_at_utc = EVALUATED_AT + timedelta(minutes=10)
    first_page = repository.review_queue_candidate_page(
        evaluated_at_utc=evaluated_at_utc,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=None,
        limit=1,
        offset=0,
    )
    inserted = queue_candidate(index=2, candidate_scope=access_scope())
    repository.persist_candidate(
        inserted,
        idempotency_key="signal-ingestion:high-cash:snapshot-backdated",
        payload={"candidateId": inserted.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    with pytest.raises(ReviewQueueSnapshotConflictError):
        repository.review_queue_candidate_page(
            evaluated_at_utc=evaluated_at_utc,
            expected_snapshot_token=first_page.snapshot_token,
            policy_version=QUEUE_POLICY_VERSION,
            access_scope_filter=None,
            limit=1,
            offset=1,
        )


def test_postgres_review_queue_token_ignores_insert_after_as_of_boundary() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    for index in (0, 1):
        candidate = queue_candidate(index=index, candidate_scope=access_scope())
        repository.persist_candidate(
            candidate,
            idempotency_key=f"signal-ingestion:high-cash:future-boundary-{index}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
    evaluated_at_utc = EVALUATED_AT + timedelta(minutes=10)
    first_page = repository.review_queue_candidate_page(
        evaluated_at_utc=evaluated_at_utc,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=None,
        limit=1,
        offset=0,
    )
    future = queue_candidate(index=11, candidate_scope=access_scope())
    repository.persist_candidate(
        future,
        idempotency_key="signal-ingestion:high-cash:future-boundary-insert",
        payload={"candidateId": future.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    second_page = repository.review_queue_candidate_page(
        evaluated_at_utc=evaluated_at_utc,
        expected_snapshot_token=first_page.snapshot_token,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=None,
        limit=1,
        offset=1,
    )

    assert second_page.snapshot_token == first_page.snapshot_token
    assert second_page.total_reviewable_item_count == 2
    assert [record.candidate.candidate_id for record in second_page.candidate_records] == [
        "idea_queue_001"
    ]


def test_postgres_review_queue_quarantines_contradictory_raw_candidate_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    valid_candidate = queue_candidate(index=1, candidate_scope=access_scope())
    repository.persist_candidate(
        valid_candidate,
        idempotency_key="signal-ingestion:high-cash:valid-state",
        payload={"candidateId": valid_candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    raw_row = connection.rows["idea_candidate_record"][0]
    raw_row["lifecycle_status"] = IdeaLifecycleStatus.CLOSED.value
    raw_row["review_posture"] = ReviewPosture.PM_REVIEW_REQUIRED.value
    raw_row["candidate_json"]["lifecycle_status"] = IdeaLifecycleStatus.CLOSED.value
    raw_row["candidate_json"]["review_posture"] = ReviewPosture.PM_REVIEW_REQUIRED.value

    page = repository.review_queue_candidate_page(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=None,
        limit=10,
        offset=0,
    )
    readiness = repository.review_queue_readiness_summary(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        access_scope_filter=None,
    )

    assert page.candidate_records == ()
    assert page.total_reviewable_item_count == 0
    assert readiness.reviewable_item_count == 0
    assert readiness.exclusion_counts["invalid_state"] == 1


def test_postgres_review_queue_scope_filters_cover_all_indexed_fields_and_stable_bounds() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    in_scope = queue_candidate(index=1, candidate_scope=access_scope())
    wrong_tenant = queue_candidate(
        index=2,
        candidate_scope=ReviewAccessScope(
            tenant_id="tenant-out-of-scope",
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
    )
    wrong_client = queue_candidate(
        index=3,
        candidate_scope=ReviewAccessScope(
            tenant_id="tenant-001",
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-out-of-scope",
        ),
    )
    for candidate in (in_scope, wrong_tenant, wrong_client):
        repository.persist_candidate(
            candidate,
            idempotency_key=f"signal-ingestion:high-cash:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
    connection.executed_sql.clear()

    page = PostgresIdeaRepository(connection).review_queue_candidate_page(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=QueueAccessScopeFilter(
            tenant_id="tenant-001",
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
        limit=10,
        offset=0,
    )

    assert [record.candidate.candidate_id for record in page.candidate_records] == [
        in_scope.candidate_id
    ]
    assert page.total_reviewable_item_count == 1
    executed_sql = " ".join(connection.executed_sql)
    for field_name in REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS:
        assert f"candidate_json->'access_scope'->>'{field_name}'" in executed_sql
    assert "order by queue_score desc, queue_created_at_utc, candidate_id" in executed_sql
    assert "limit %s offset %s" in executed_sql


def test_postgres_review_queue_readiness_summary_uses_bounded_candidate_aggregate() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    reviewable = queue_candidate(index=1, candidate_scope=access_scope())
    duplicate = replace(
        queue_candidate(index=2, candidate_scope=access_scope()),
        source_signal_ids=reviewable.source_signal_ids,
    )
    expired = replace(
        queue_candidate(index=3, candidate_scope=access_scope()),
        lifecycle_status=IdeaLifecycleStatus.EXPIRED,
        review_posture=ReviewPosture.NO_ACTION,
    )
    blocked = queue_candidate(index=4, candidate_scope=access_scope())
    blocked = replace(
        blocked,
        evidence_packet=replace(
            blocked.evidence_packet,
            supportability=EvidenceSupportability.BLOCKED,
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        ),
    )
    unscored = replace(queue_candidate(index=5, candidate_scope=access_scope()), score=None)
    out_of_scope = queue_candidate(
        index=6,
        candidate_scope=ReviewAccessScope(
            tenant_id="tenant-001",
            book_id="book-001",
            portfolio_id="portfolio-out-of-scope",
            client_id="client-001",
        ),
    )
    for candidate in (reviewable, duplicate, expired, blocked, unscored, out_of_scope):
        repository.persist_candidate(
            candidate,
            idempotency_key=f"signal-ingestion:high-cash:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
    connection.executed_sql.clear()

    summary = load_review_queue_readiness_summary(
        connection,
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        access_scope_filter=QueueAccessScopeFilter(portfolio_id="portfolio-001"),
    )

    assert summary.candidate_snapshot_count == 6
    assert summary.reviewable_item_count == 1
    assert summary.excluded_candidate_count == 5
    assert summary.exclusion_counts["duplicate"] == 1
    assert summary.exclusion_counts["expired"] == 1
    assert summary.exclusion_counts["unsupported_evidence"] == 1
    assert summary.exclusion_counts["unscored"] == 1
    assert summary.exclusion_counts["access_scope_mismatch"] == 1
    assert summary.scored_candidate_count == 5
    assert summary.unscored_candidate_count == 1
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea review-queue-readiness-summary */" in executed_sql
    assert "idea_candidate_record" in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql
    assert "idea_report_evidence_pack_request" not in executed_sql
    assert "idea_ai_explanation_lineage" not in executed_sql
    assert "idea_audit_event" not in executed_sql
    assert "idea_idempotency_record" not in executed_sql


def test_review_queue_candidate_page_rejects_unsafe_page_controls() -> None:
    connection = FakePostgresConnection()

    with pytest.raises(ValueError, match="limit must be positive"):
        load_review_queue_candidate_page(
            connection,
            evaluated_at_utc=QUEUE_EVALUATED_AT,
            expected_snapshot_token=None,
            policy_version=QUEUE_POLICY_VERSION,
            access_scope_filter=None,
            limit=0,
            offset=0,
        )
    with pytest.raises(ValueError, match="offset must be greater than or equal to zero"):
        load_review_queue_candidate_page(
            connection,
            evaluated_at_utc=QUEUE_EVALUATED_AT,
            expected_snapshot_token=None,
            policy_version=QUEUE_POLICY_VERSION,
            access_scope_filter=None,
            limit=1,
            offset=-1,
        )


def test_review_queue_predicates_use_postgres_array_parameters() -> None:
    _predicate_sql, params = _review_queue_candidate_predicates(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        access_scope_filter=QueueAccessScopeFilter(portfolio_id="portfolio-001"),
    )

    assert params[0] == QUEUE_EVALUATED_AT
    assert isinstance(params[1], list)
    assert isinstance(params[4], list)
    assert params[4] == ["portfolio-001"]


def test_review_queue_predicates_keep_scope_parameter_order_aligned_to_indexes() -> None:
    predicate_sql, params = _review_queue_candidate_predicates(
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        access_scope_filter=QueueAccessScopeFilter(
            tenant_id="tenant-001",
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
    )

    assert REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS == (
        "tenant_id",
        "book_id",
        "portfolio_id",
        "client_id",
    )
    assert [
        predicate_sql.index(f"->>'{field_name}'")
        for field_name in REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS
    ] == sorted(
        predicate_sql.index(f"->>'{field_name}'")
        for field_name in REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS
    )
    assert params[4:] == (
        ["tenant-001"],
        ["book-001"],
        ["portfolio-001"],
        ["client-001"],
    )


def test_review_queue_candidate_page_handles_empty_count_result() -> None:
    connection = EmptyReviewQueueConnection()

    page = load_review_queue_candidate_page(
        connection,
        evaluated_at_utc=QUEUE_EVALUATED_AT,
        expected_snapshot_token=None,
        policy_version=QUEUE_POLICY_VERSION,
        access_scope_filter=None,
        limit=10,
        offset=0,
    )

    assert page.candidate_records == ()
    assert page.total_reviewable_item_count == 0
    assert page.total_excluded_candidate_count == 0
    assert "/* lotus-idea review-queue-count */" in " ".join(connection.executed_sql)
    assert "/* lotus-idea review-queue-page */" in " ".join(connection.executed_sql)


def queue_candidate(
    *,
    index: int,
    candidate_scope: ReviewAccessScope | None,
) -> IdeaCandidate:
    return replace(
        high_cash_candidate(candidate_scope=candidate_scope),
        candidate_id=f"idea_queue_{index:03d}",
        source_signal_ids=(f"signal_queue_{index:03d}",),
        created_at_utc=EVALUATED_AT + timedelta(minutes=index),
        updated_at_utc=EVALUATED_AT + timedelta(minutes=index),
    )


class EmptyReviewQueueConnection:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def cursor(self) -> "EmptyReviewQueueCursor":
        return EmptyReviewQueueCursor(self)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class EmptyReviewQueueCursor:
    def __init__(self, connection: EmptyReviewQueueConnection) -> None:
        self.connection = connection

    def execute(self, query: str, params: object | None = None) -> None:
        del params
        self.connection.executed_sql.append(" ".join(query.lower().split()))

    def fetchall(self) -> list[dict[str, Any]]:
        return []

    def __enter__(self) -> "EmptyReviewQueueCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None
