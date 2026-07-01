from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.domain import OutboxEventStatus
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    high_cash_candidate,
)


def test_postgres_repository_uses_outbox_only_readiness_projection() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:outbox-readiness-projection",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    base_row = dict(connection.rows["idea_outbox_event"][0])
    connection.rows["idea_outbox_event"] = [
        _outbox_row(base_row, "event-pending", OutboxEventStatus.PENDING),
        _outbox_row(
            base_row,
            "event-leased-active",
            OutboxEventStatus.LEASED,
            lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
        ),
        _outbox_row(
            base_row,
            "event-leased-expired",
            OutboxEventStatus.LEASED,
            lease_expires_at_utc=EVALUATED_AT - timedelta(minutes=1),
        ),
        _outbox_row(
            base_row,
            "event-failed-retryable",
            OutboxEventStatus.FAILED,
            retry_count=1,
        ),
        _outbox_row(
            base_row,
            "event-failed-deferred",
            OutboxEventStatus.FAILED,
            retry_count=1,
            next_attempt_at_utc=EVALUATED_AT + timedelta(minutes=5),
        ),
        _outbox_row(base_row, "event-published", OutboxEventStatus.PUBLISHED),
        _outbox_row(base_row, "event-dead-letter", OutboxEventStatus.DEAD_LETTER),
    ]
    connection.executed_sql.clear()

    summary = repository.outbox_delivery_readiness_summary(
        max_retry_count=3,
        evaluated_at_utc=EVALUATED_AT,
    )

    executed_sql = " ".join(connection.executed_sql)
    assert summary.pending_count == 1
    assert summary.leased_count == 2
    assert summary.failed_count == 2
    assert summary.published_count == 1
    assert summary.dead_letter_count == 1
    assert summary.expired_lease_count == 1
    assert summary.delivery_ready_count == 3
    assert summary.retry_deferred_count == 1
    assert "/* lotus-idea outbox-readiness-summary */" in executed_sql
    assert "from idea_outbox_event" in executed_sql
    for unrelated_table in (
        "idea_candidate_record",
        "idea_audit_event",
        "idea_review_decision",
        "idea_downstream_submission",
        "idea_conversion_intent",
        "idea_report_evidence_pack_request",
        "idea_ai_explanation_lineage",
    ):
        assert unrelated_table not in executed_sql


def _outbox_row(
    base_row: dict[str, Any],
    event_id: str,
    status: OutboxEventStatus,
    *,
    retry_count: int = 0,
    lease_expires_at_utc: datetime | None = None,
    next_attempt_at_utc: datetime | None = None,
) -> dict[str, Any]:
    row = dict(base_row)
    row["outbox_event_id"] = event_id
    row["status"] = status.value
    row["retry_count"] = retry_count
    row["lease_expires_at_utc"] = lease_expires_at_utc
    row["lease_owner"] = "worker-1" if status is OutboxEventStatus.LEASED else None
    row["lease_attempt_id"] = f"{event_id}:lease" if status is OutboxEventStatus.LEASED else None
    row["published_at_utc"] = EVALUATED_AT if status is OutboxEventStatus.PUBLISHED else None
    row["failure_reason"] = "publisher_unavailable" if status is OutboxEventStatus.FAILED else None
    row["first_failed_at_utc"] = (
        EVALUATED_AT - timedelta(minutes=5) if status is OutboxEventStatus.FAILED else None
    )
    row["last_failed_at_utc"] = (
        EVALUATED_AT - timedelta(minutes=5) if status is OutboxEventStatus.FAILED else None
    )
    row["next_attempt_at_utc"] = next_attempt_at_utc
    if status is OutboxEventStatus.FAILED and next_attempt_at_utc is None:
        row["next_attempt_at_utc"] = EVALUATED_AT - timedelta(minutes=1)
    return row
