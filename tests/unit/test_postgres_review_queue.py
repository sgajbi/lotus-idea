from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from app.domain import IdeaCandidate, QueueAccessScopeFilter, ReviewAccessScope
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_review_queue import load_review_queue_candidate_page
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    high_cash_candidate,
)


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


def test_review_queue_candidate_page_rejects_unsafe_page_controls() -> None:
    connection = FakePostgresConnection()

    with pytest.raises(ValueError, match="limit must be positive"):
        load_review_queue_candidate_page(
            connection,
            access_scope_filter=None,
            limit=0,
            offset=0,
        )
    with pytest.raises(ValueError, match="offset must be greater than or equal to zero"):
        load_review_queue_candidate_page(
            connection,
            access_scope_filter=None,
            limit=1,
            offset=-1,
        )


def test_review_queue_candidate_page_handles_empty_count_result() -> None:
    connection = EmptyReviewQueueConnection()

    page = load_review_queue_candidate_page(
        connection,
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
