from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxDeliveryDecision,
    OutboxEventRecord,
    OutboxEventStatus,
    SUPPORTED_OUTBOX_EVENT_TYPES,
    build_candidate_outbox_event,
    lease_outbox_event,
    mark_outbox_event_failed,
    validate_outbox_failure_reason,
)


EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def outbox_repository() -> tuple[InMemoryIdeaRepository, OutboxEventRecord]:
    event = build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="idea-high-cash-001",
        occurred_at_utc=EVALUATED_AT,
        payload={"source_hash": "sha256:portfolio-state"},
        idempotency_key="signal-ingestion:outbox-event:001",
    )
    repository = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            outbox_events={event.event_id: event},
        )
    )
    return repository, event


def event_record(
    *,
    status: OutboxEventStatus = OutboxEventStatus.PENDING,
    published_at_utc: datetime | None = None,
    failure_reason: str | None = None,
    first_failed_at_utc: datetime | None = None,
    last_failed_at_utc: datetime | None = None,
    next_attempt_at_utc: datetime | None = None,
    lease_owner: str | None = None,
    lease_attempt_id: str | None = None,
    lease_expires_at_utc: datetime | None = None,
) -> OutboxEventRecord:
    return OutboxEventRecord(
        event_id="evt_invalid_state",
        event_type="idea.candidate.persisted.v1",
        aggregate_type="idea_candidate",
        aggregate_id="idea-high-cash-001",
        schema_version="v1",
        payload={"candidate_family": "high_cash"},
        occurred_at_utc=EVALUATED_AT,
        status=status,
        published_at_utc=published_at_utc,
        failure_reason=failure_reason,
        first_failed_at_utc=first_failed_at_utc,
        last_failed_at_utc=last_failed_at_utc,
        next_attempt_at_utc=next_attempt_at_utc,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=lease_expires_at_utc,
    )


def claim_event(
    repository: InMemoryIdeaRepository,
    event_id: str,
    *,
    attempt_id: str,
    owner: str = "worker-1",
    claimed_at_utc: datetime = EVALUATED_AT,
) -> OutboxEventRecord:
    claimed = repository.claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=3,
        lease_owner=owner,
        lease_attempt_id=attempt_id,
        claimed_at_utc=claimed_at_utc,
        lease_expires_at_utc=claimed_at_utc + timedelta(minutes=5),
    )
    for event in claimed:
        if event.event_id == event_id:
            return event
    raise AssertionError(f"event was not claimed: {event_id}")


def test_outbox_event_payload_rejects_sensitive_source_and_client_keys() -> None:
    with pytest.raises(ValueError, match="sensitive keys"):
        build_candidate_outbox_event(
            event_type="idea.candidate.persisted.v1",
            aggregate_id="idea_high_cash_001",
            occurred_at_utc=EVALUATED_AT,
            payload={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            idempotency_key="signal-ingestion:high-cash:001",
        )


@pytest.mark.parametrize("event_type", SUPPORTED_OUTBOX_EVENT_TYPES)
def test_outbox_event_accepts_governed_event_families(event_type: str) -> None:
    event = build_candidate_outbox_event(
        event_type=event_type,
        aggregate_id="idea-high-cash-001",
        occurred_at_utc=EVALUATED_AT,
        payload={"candidate_family": "high_cash"},
    )

    assert event.event_type == event_type
    assert event.schema_version == "v1"


def test_outbox_event_rejects_unknown_event_type_and_schema_version() -> None:
    with pytest.raises(ValueError, match="unsupported outbox event_type"):
        build_candidate_outbox_event(
            event_type="idea.uncontracted.event.v1",
            aggregate_id="idea-high-cash-001",
            occurred_at_utc=EVALUATED_AT,
            payload={"candidate_family": "high_cash"},
        )
    with pytest.raises(ValueError, match="unsupported outbox schema_version"):
        OutboxEventRecord(
            event_id="evt_wrong_schema",
            event_type="idea.candidate.persisted.v1",
            aggregate_type="idea_candidate",
            aggregate_id="idea-high-cash-001",
            schema_version="v2",
            payload={"candidate_family": "high_cash"},
            occurred_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="unsupported outbox aggregate_type"):
        OutboxEventRecord(
            event_id="evt_wrong_aggregate",
            event_type="idea.candidate.persisted.v1",
            aggregate_type="portfolio",
            aggregate_id="idea-high-cash-001",
            schema_version="v1",
            payload={"candidate_family": "high_cash"},
            occurred_at_utc=EVALUATED_AT,
        )


def test_outbox_event_rejects_invalid_lease_and_failure_state() -> None:
    with pytest.raises(ValueError, match="lease_owner is required"):
        event_record(status=OutboxEventStatus.LEASED)
    with pytest.raises(ValueError, match="lease metadata is allowed only for leased"):
        event_record(lease_owner="worker-1")
    with pytest.raises(ValueError, match="published_at_utc is required"):
        event_record(status=OutboxEventStatus.PUBLISHED)
    with pytest.raises(ValueError, match="first_failed_at_utc is required"):
        event_record(
            status=OutboxEventStatus.FAILED,
            failure_reason="publisher_unavailable",
        )
    with pytest.raises(ValueError, match="last_failed_at_utc is required"):
        event_record(
            status=OutboxEventStatus.FAILED,
            failure_reason="publisher_unavailable",
            first_failed_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="leased outbox failure timing"):
        event_record(
            status=OutboxEventStatus.LEASED,
            lease_owner="worker-1",
            lease_attempt_id="attempt-1",
            lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
            first_failed_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="leased outbox events cannot have next_attempt_at_utc"):
        event_record(
            status=OutboxEventStatus.LEASED,
            lease_owner="worker-1",
            lease_attempt_id="attempt-1",
            lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
            next_attempt_at_utc=EVALUATED_AT + timedelta(seconds=60),
        )
    with pytest.raises(ValueError, match="failure timing is allowed only"):
        event_record(first_failed_at_utc=EVALUATED_AT)


def test_outbox_failure_transition_rejects_unsafe_retry_and_dead_letter_timing() -> None:
    event = build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="idea-high-cash-001",
        occurred_at_utc=EVALUATED_AT,
        payload={"source_hash": "sha256:portfolio-state"},
    )
    leased = lease_outbox_event(
        event,
        lease_owner="worker-1",
        lease_attempt_id="attempt-1",
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="next_attempt_at_utc is required"):
        mark_outbox_event_failed(
            leased,
            failure_reason="publisher_unavailable",
            failed_at_utc=EVALUATED_AT,
            max_retry_count=2,
            next_attempt_at_utc=None,
        )
    with pytest.raises(ValueError, match="next_attempt_at_utc must be after failed_at_utc"):
        mark_outbox_event_failed(
            leased,
            failure_reason="publisher_unavailable",
            failed_at_utc=EVALUATED_AT,
            max_retry_count=2,
            next_attempt_at_utc=EVALUATED_AT,
        )
    with pytest.raises(ValueError, match="dead-lettered outbox events cannot have"):
        mark_outbox_event_failed(
            leased,
            failure_reason="publisher_unavailable",
            failed_at_utc=EVALUATED_AT,
            max_retry_count=1,
            next_attempt_at_utc=EVALUATED_AT + timedelta(seconds=60),
        )
    with pytest.raises(ValueError, match="max_retry_count must be positive"):
        mark_outbox_event_failed(
            leased,
            failure_reason="publisher_unavailable",
            failed_at_utc=EVALUATED_AT,
            max_retry_count=0,
            next_attempt_at_utc=None,
        )
    with pytest.raises(ValueError, match="sensitive keys"):
        validate_outbox_failure_reason("account_id leaked by publisher")


def test_outbox_delivery_marks_events_published_failed_and_dead_lettered() -> None:
    repository, event = outbox_repository()

    claimed = claim_event(repository, event.event_id, attempt_id="attempt-failed-1")
    failed = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-failed-1",
        failure_reason="publisher_unavailable",
        failed_at_utc=EVALUATED_AT,
        max_retry_count=2,
    )
    retryable = repository.outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        evaluated_at_utc=EVALUATED_AT + timedelta(seconds=59),
    )
    due_retryable = repository.outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        evaluated_at_utc=EVALUATED_AT + timedelta(seconds=60),
    )
    claimed_retry = claim_event(
        repository,
        event.event_id,
        attempt_id="attempt-failed-2",
        claimed_at_utc=EVALUATED_AT + timedelta(seconds=60),
    )
    dead_lettered = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-failed-2",
        failure_reason="publisher_unavailable",
        failed_at_utc=EVALUATED_AT + timedelta(seconds=60),
        max_retry_count=2,
    )
    delivered = repository.outbox_events_for_delivery(limit=10, max_retry_count=2)
    published_after_dead_letter = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-failed-2",
        published_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
    )
    failed_after_dead_letter = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-failed-2",
        failure_reason="publisher_unavailable",
        max_retry_count=2,
    )

    assert claimed.status is OutboxEventStatus.LEASED
    assert failed.decision is OutboxDeliveryDecision.ACCEPTED
    assert failed.event is not None
    assert failed.event.status is OutboxEventStatus.FAILED
    assert failed.event.retry_count == 1
    assert failed.event.first_failed_at_utc == EVALUATED_AT
    assert failed.event.last_failed_at_utc == EVALUATED_AT
    assert failed.event.next_attempt_at_utc == EVALUATED_AT + timedelta(seconds=60)
    assert retryable == ()
    assert due_retryable == (failed.event,)
    assert claimed_retry.status is OutboxEventStatus.LEASED
    assert claimed_retry.first_failed_at_utc == EVALUATED_AT
    assert claimed_retry.last_failed_at_utc == EVALUATED_AT
    assert claimed_retry.next_attempt_at_utc is None
    assert dead_lettered.decision is OutboxDeliveryDecision.DEAD_LETTERED
    assert dead_lettered.event is not None
    assert dead_lettered.event.status is OutboxEventStatus.DEAD_LETTER
    assert dead_lettered.event.retry_count == 2
    assert dead_lettered.event.first_failed_at_utc == EVALUATED_AT
    assert dead_lettered.event.last_failed_at_utc == EVALUATED_AT + timedelta(seconds=60)
    assert dead_lettered.event.next_attempt_at_utc is None
    assert delivered == ()
    assert published_after_dead_letter.decision is OutboxDeliveryDecision.DEAD_LETTERED
    assert failed_after_dead_letter.decision is OutboxDeliveryDecision.DEAD_LETTERED


def test_outbox_delivery_marks_event_published_once() -> None:
    repository, event = outbox_repository()

    claimed = claim_event(repository, event.event_id, attempt_id="attempt-publish-1")
    published = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-publish-1",
        published_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
    )
    second = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-publish-1",
        published_at_utc=datetime(2026, 6, 21, 10, 2, tzinfo=UTC),
    )

    assert claimed.status is OutboxEventStatus.LEASED
    assert published.decision is OutboxDeliveryDecision.ACCEPTED
    assert published.event is not None
    assert published.event.status is OutboxEventStatus.PUBLISHED
    assert published.event.published_at_utc == datetime(2026, 6, 21, 10, 1, tzinfo=UTC)
    assert published.event.failure_reason is None
    assert second.decision is OutboxDeliveryDecision.ALREADY_PUBLISHED
    assert repository.outbox_events_for_delivery() == ()


def test_outbox_delivery_returns_not_found_and_terminal_statuses() -> None:
    repository, event = outbox_repository()

    missing_publish = repository.mark_outbox_event_published(
        "missing-event",
        lease_owner="worker-1",
        lease_attempt_id="missing-attempt",
        published_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
    )
    missing_failure = repository.mark_outbox_event_failed(
        "missing-event",
        lease_owner="worker-1",
        lease_attempt_id="missing-attempt",
        failure_reason="publisher_unavailable",
    )
    claimed = claim_event(repository, event.event_id, attempt_id="attempt-terminal-1")
    published = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-terminal-1",
        published_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
    )
    failed_after_published = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-terminal-1",
        failure_reason="publisher_unavailable",
    )

    assert missing_publish.decision is OutboxDeliveryDecision.NOT_FOUND
    assert missing_publish.event is None
    assert missing_failure.decision is OutboxDeliveryDecision.NOT_FOUND
    assert missing_failure.event is None
    assert claimed.status is OutboxEventStatus.LEASED
    assert published.decision is OutboxDeliveryDecision.ACCEPTED
    assert failed_after_published.decision is OutboxDeliveryDecision.ALREADY_PUBLISHED


def test_outbox_delivery_rejects_invalid_delivery_arguments() -> None:
    repository = InMemoryIdeaRepository()

    with pytest.raises(ValueError, match="limit must be positive"):
        repository.outbox_events_for_delivery(limit=0)
    with pytest.raises(ValueError, match="event_id is required"):
        repository.mark_outbox_event_published(
            " ",
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid",
            published_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="published_at_utc must be timezone-aware"):
        repository.mark_outbox_event_published(
            "missing-event",
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid",
            published_at_utc=datetime(2026, 6, 21, 10, 1),
        )


def test_outbox_failure_reason_rejects_sensitive_identifiers() -> None:
    repository, event = outbox_repository()
    claim_event(repository, event.event_id, attempt_id="attempt-sensitive")

    with pytest.raises(ValueError, match="sensitive keys"):
        repository.mark_outbox_event_failed(
            event.event_id,
            lease_owner="worker-1",
            lease_attempt_id="attempt-sensitive",
            failure_reason="portfolio_id leaked in downstream error",
        )
