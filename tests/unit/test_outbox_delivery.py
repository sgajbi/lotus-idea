from __future__ import annotations

from datetime import UTC, datetime

from app.application.outbox_delivery import (
    OutboxPublishOutcome,
    run_outbox_delivery_once,
)
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventRecord,
    OutboxEventStatus,
    build_candidate_outbox_event,
)


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
DELIVERED_AT = datetime(2026, 6, 21, 10, 5, tzinfo=UTC)


class AcceptingPublisher:
    def __init__(self) -> None:
        self.events: list[OutboxEventRecord] = []

    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        self.events.append(event)
        return OutboxPublishOutcome.accepted_by_publisher()


class RejectingPublisher:
    def __init__(self, failure_reason: str = "publisher_rejected") -> None:
        self.failure_reason = failure_reason

    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        return OutboxPublishOutcome.rejected_by_publisher(self.failure_reason)


class RaisingPublisher:
    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        raise RuntimeError("raw downstream exception must not leak")


def test_run_outbox_delivery_once_marks_published_events_source_safely() -> None:
    event = outbox_event("idea.candidate.persisted.v1")
    repository = repository_with_events(event)
    publisher = AcceptingPublisher()

    summary = run_outbox_delivery_once(
        repository,
        publisher,
        delivered_at_utc=DELIVERED_AT,
    )
    published = repository.snapshot().outbox_events[event.event_id]

    assert summary.attempted_count == 1
    assert summary.published_count == 1
    assert summary.failed_count == 0
    assert summary.dead_lettered_count == 0
    assert summary.external_broker_publication_supported is False
    assert publisher.events == [event]
    assert published.status is OutboxEventStatus.PUBLISHED
    assert published.published_at_utc == DELIVERED_AT


def test_run_outbox_delivery_once_retries_then_dead_letters_failed_events() -> None:
    event = outbox_event("idea.lifecycle.transitioned.v1")
    repository = repository_with_events(event)

    first = run_outbox_delivery_once(
        repository,
        RejectingPublisher(),
        max_retry_count=2,
        delivered_at_utc=DELIVERED_AT,
    )
    second = run_outbox_delivery_once(
        repository,
        RejectingPublisher(),
        max_retry_count=2,
        delivered_at_utc=DELIVERED_AT,
    )
    dead_lettered = repository.snapshot().outbox_events[event.event_id]

    assert first.attempted_count == 1
    assert first.failed_count == 1
    assert first.dead_lettered_count == 0
    assert second.attempted_count == 1
    assert second.failed_count == 0
    assert second.dead_lettered_count == 1
    assert dead_lettered.status is OutboxEventStatus.DEAD_LETTER
    assert dead_lettered.retry_count == 2


def test_run_outbox_delivery_once_maps_exceptions_to_bounded_failure_reason() -> None:
    event = outbox_event("idea.feedback.recorded.v1")
    repository = repository_with_events(event)

    summary = run_outbox_delivery_once(
        repository,
        RaisingPublisher(),
        max_retry_count=3,
        delivered_at_utc=DELIVERED_AT,
    )
    failed = repository.snapshot().outbox_events[event.event_id]

    assert summary.failed_count == 1
    assert failed.status is OutboxEventStatus.FAILED
    assert failed.failure_reason == "publisher_unavailable"


def outbox_event(event_type: str) -> OutboxEventRecord:
    return build_candidate_outbox_event(
        event_type=event_type,
        aggregate_id="idea_high_cash_001",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
        idempotency_key=f"{event_type}:idempotency",
    )


def repository_with_events(*events: OutboxEventRecord) -> InMemoryIdeaRepository:
    return InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            outbox_events={event.event_id: event for event in events},
        )
    )
