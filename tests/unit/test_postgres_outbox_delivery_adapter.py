from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.domain import OutboxDeliveryDecision, OutboxEventStatus
from app.infrastructure.postgres_outbox_delivery import (
    claim_outbox_events_for_delivery,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    FakePostgresConnection,
    high_cash_candidate,
)


class RaisingCursor:
    def execute(self, _query: str, _params: object | None = None) -> None:
        raise RuntimeError("database write failed")

    def fetchall(self) -> list[object]:
        return []

    def __enter__(self) -> RaisingCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class RollbackAwareConnection:
    def __init__(self) -> None:
        self.rollbacks = 0

    def cursor(self) -> RaisingCursor:
        return RaisingCursor()

    def commit(self) -> None:
        raise AssertionError("commit must not run after failed outbox mutation")

    def rollback(self) -> None:
        self.rollbacks += 1


def test_postgres_outbox_adapter_reports_dead_lettered_delivery_races() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:outbox-dead-letter-race",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    event = next(iter(PostgresIdeaRepository(connection).snapshot().outbox_events.values()))
    repository.claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=1,
        lease_owner="worker-1",
        lease_attempt_id="attempt-dead-letter",
        claimed_at_utc=EVALUATED_AT,
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
    )

    dead_lettered = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-dead-letter",
        failure_reason="publisher_rejected",
        max_retry_count=1,
    )
    publish_after_dead_letter = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-dead-letter",
        published_at_utc=EVALUATED_AT + timedelta(minutes=1),
    )

    assert dead_lettered.decision is OutboxDeliveryDecision.DEAD_LETTERED
    assert dead_lettered.event is not None
    assert dead_lettered.event.status is OutboxEventStatus.DEAD_LETTER
    assert publish_after_dead_letter.decision is OutboxDeliveryDecision.DEAD_LETTERED


def test_postgres_outbox_adapter_validates_delivery_lease_inputs() -> None:
    repository = PostgresIdeaRepository(FakePostgresConnection())

    with pytest.raises(ValueError, match="lease_expires_at_utc must be after claimed_at_utc"):
        repository.claim_outbox_events_for_delivery(
            limit=10,
            max_retry_count=2,
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid-window",
            claimed_at_utc=EVALUATED_AT,
            lease_expires_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="event_id is required"):
        repository.mark_outbox_event_published(
            " ",
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid-event",
            published_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="max_retry_count must be positive"):
        repository.mark_outbox_event_failed(
            "event-1",
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid-retry",
            failure_reason="publisher_unavailable",
            max_retry_count=0,
        )
    with pytest.raises(ValueError, match="claimed_at_utc must be timezone-aware"):
        repository.claim_outbox_events_for_delivery(
            limit=10,
            max_retry_count=2,
            lease_owner="worker-1",
            lease_attempt_id="attempt-naive-claim",
            claimed_at_utc=datetime(2026, 6, 21, 10, 0),
            lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
        )
    with pytest.raises(ValueError, match="published_at_utc must be UTC"):
        repository.mark_outbox_event_published(
            "event-1",
            lease_owner="worker-1",
            lease_attempt_id="attempt-nonutc-publish",
            published_at_utc=datetime(2026, 6, 21, 11, 0, tzinfo=timezone(timedelta(hours=1))),
        )


@pytest.mark.parametrize("operation", ["claim", "publish", "fail"])
def test_postgres_outbox_adapter_rolls_back_failed_delivery_mutations(operation: str) -> None:
    connection = RollbackAwareConnection()

    with pytest.raises(RuntimeError, match="database write failed"):
        if operation == "claim":
            claim_outbox_events_for_delivery(
                connection,
                limit=10,
                max_retry_count=2,
                lease_owner="worker-1",
                lease_attempt_id="attempt-rollback",
                claimed_at_utc=EVALUATED_AT,
                lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
            )
        elif operation == "publish":
            mark_outbox_event_published(
                connection,
                "event-1",
                lease_owner="worker-1",
                lease_attempt_id="attempt-rollback",
                published_at_utc=EVALUATED_AT,
            )
        else:
            mark_outbox_event_failed(
                connection,
                "event-1",
                lease_owner="worker-1",
                lease_attempt_id="attempt-rollback",
                failure_reason="publisher_unavailable",
                max_retry_count=2,
            )

    assert connection.rollbacks == 1
