from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, TypedDict

import pytest

from app.domain import (
    OutboxDeliveryDecision,
    OutboxEventStatus,
    OutboxRecoveryDecision,
    outbox_dead_letter_support_reference,
    outbox_recovery_request_payload,
)
from app.infrastructure.postgres_outbox_delivery import (
    claim_outbox_events_for_delivery,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    high_cash_candidate,
)


class RecoveryClaim(TypedDict):
    support_reference: str
    idempotency_key: str
    request_payload: Mapping[str, Any]
    actor_subject: str
    reason: str
    change_reference: str
    requested_at_utc: datetime
    lease_owner: str
    lease_attempt_id: str
    lease_expires_at_utc: datetime


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
    claim_sql = next(query for query in connection.executed_sql if "with selected as" in query)
    assert "returning event.outbox_event_id" in claim_sql

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


def test_postgres_outbox_recovery_is_durable_idempotent_and_lease_fenced() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:outbox-recovery",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    event = next(iter(repository.snapshot().outbox_events.values()))
    repository.claim_outbox_events_for_delivery(
        limit=1,
        max_retry_count=1,
        lease_owner="delivery-worker",
        lease_attempt_id="delivery-attempt",
        claimed_at_utc=EVALUATED_AT,
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=1),
    )
    repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="delivery-worker",
        lease_attempt_id="delivery-attempt",
        failure_reason="publisher_rejected",
        failed_at_utc=EVALUATED_AT + timedelta(minutes=1),
        max_retry_count=1,
    )
    target_row = next(
        row
        for row in connection.rows["idea_outbox_event"]
        if row["outbox_event_id"] == event.event_id
    )
    connection.rows["idea_outbox_event"].extend(
        {
            **target_row,
            "outbox_event_id": f"event-newer-{index:04d}",
            "status": OutboxEventStatus.PENDING.value,
            "occurred_at_utc": EVALUATED_AT + timedelta(days=1),
        }
        for index in range(1001)
    )
    support_reference = outbox_dead_letter_support_reference(event.event_id)
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        actor_subject="platform-operator",
    )
    claim: RecoveryClaim = {
        "support_reference": support_reference,
        "idempotency_key": "outbox-redrive:postgres:001",
        "request_payload": request_payload,
        "actor_subject": "platform-operator",
        "reason": "broker_route_corrected",
        "change_reference": "CHG-2026-0710",
        "requested_at_utc": EVALUATED_AT + timedelta(minutes=2),
        "lease_owner": "outbox-recovery",
        "lease_attempt_id": "recovery-attempt-1",
        "lease_expires_at_utc": EVALUATED_AT + timedelta(minutes=7),
    }

    summaries = repository.dead_letter_summaries(limit=10)
    accepted = repository.claim_dead_letter_for_recovery(**claim)
    restarted_repository = PostgresIdeaRepository(connection)
    replay = restarted_repository.claim_dead_letter_for_recovery(**claim)
    competing_claim: RecoveryClaim = {
        **claim,
        "idempotency_key": "outbox-redrive:postgres:002",
        "lease_attempt_id": "recovery-attempt-2",
    }
    competing = restarted_repository.claim_dead_letter_for_recovery(**competing_claim)

    assert [summary.support_reference for summary in summaries] == [support_reference]
    assert accepted.decision is OutboxRecoveryDecision.ACCEPTED
    assert accepted.event is not None
    assert accepted.event.status is OutboxEventStatus.LEASED
    assert accepted.event.failure_reason == "publisher_rejected"
    assert replay.decision is OutboxRecoveryDecision.REPLAYED
    assert competing.decision is OutboxRecoveryDecision.LEASE_CONFLICT
    records = restarted_repository.outbox_recovery_audit_records()
    assert len(records) == 1
    assert records[0].original_failure_reason == "publisher_rejected"
    assert records[0].original_retry_count == 1
    assert "outbox-redrive:postgres:001" not in str(connection.rows)
    lookup_sql = next(
        query
        for query in connection.executed_sql
        if "outbox-dead-letter-by-support-reference" in query
    )
    assert "where (" in lookup_sql
    assert "sha256(outbox_event_id::bytea)" in lookup_sql
    assert "order by" not in lookup_sql
    assert "limit" not in lookup_sql
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
