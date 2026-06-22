from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.application.outbox_delivery import run_outbox_delivery_once
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxDeliveryDecision,
    OutboxDeliveryResult,
    OutboxEventRecord,
    OutboxEventStatus,
    build_candidate_outbox_event,
)
from app.ports.outbox_publisher import OutboxPublishOutcome


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


class NoReasonRejectingPublisher:
    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        return OutboxPublishOutcome(accepted=False)


class DeliveryEdgeRepository:
    def __init__(
        self,
        event: OutboxEventRecord,
        *,
        publish_decision: OutboxDeliveryDecision = OutboxDeliveryDecision.ACCEPTED,
        fail_decision: OutboxDeliveryDecision = OutboxDeliveryDecision.ACCEPTED,
    ) -> None:
        self.event = event
        self.publish_decision = publish_decision
        self.fail_decision = fail_decision
        self.failure_reason: str | None = None

    def snapshot(self) -> IdeaRepositorySnapshot:
        return IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            outbox_events={self.event.event_id: self.event},
        )

    def outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
    ) -> tuple[OutboxEventRecord, ...]:
        return (self.event,)

    def mark_outbox_event_published(
        self,
        event_id: str,
        *,
        published_at_utc: datetime,
    ) -> OutboxDeliveryResult:
        return OutboxDeliveryResult(decision=self.publish_decision, event=self.event)

    def mark_outbox_event_failed(
        self,
        event_id: str,
        *,
        failure_reason: str,
        max_retry_count: int = 3,
    ) -> OutboxDeliveryResult:
        self.failure_reason = failure_reason
        return OutboxDeliveryResult(decision=self.fail_decision, event=self.event)


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


def test_run_outbox_delivery_once_skips_non_deliverable_events() -> None:
    event = OutboxEventRecord(
        event_id="evt_already_published",
        event_type="idea.candidate.persisted.v1",
        aggregate_type="idea_candidate",
        aggregate_id="idea_high_cash_001",
        schema_version="v1",
        payload={"candidate_family": "high_cash"},
        occurred_at_utc=EVENT_TIME,
        status=OutboxEventStatus.PUBLISHED,
        published_at_utc=DELIVERED_AT,
    )
    repository = DeliveryEdgeRepository(event)

    summary = run_outbox_delivery_once(
        repository,
        AcceptingPublisher(),
        delivered_at_utc=DELIVERED_AT,
    )

    assert summary.attempted_count == 1
    assert summary.skipped_count == 1
    assert summary.published_count == 0


def test_run_outbox_delivery_once_counts_repository_race_as_skipped() -> None:
    event = outbox_event("idea.review.recorded.v1")
    repository = DeliveryEdgeRepository(
        event,
        publish_decision=OutboxDeliveryDecision.ALREADY_PUBLISHED,
    )

    summary = run_outbox_delivery_once(
        repository,
        AcceptingPublisher(),
        delivered_at_utc=DELIVERED_AT,
    )

    assert summary.attempted_count == 1
    assert summary.skipped_count == 1
    assert summary.published_count == 0


def test_run_outbox_delivery_once_uses_bounded_default_failure_reason() -> None:
    event = outbox_event("idea.report.requested.v1")
    repository = DeliveryEdgeRepository(event)

    summary = run_outbox_delivery_once(
        repository,
        NoReasonRejectingPublisher(),
        delivered_at_utc=DELIVERED_AT,
    )

    assert summary.failed_count == 1
    assert repository.failure_reason == "publisher_rejected"


def test_run_outbox_delivery_once_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        run_outbox_delivery_once(
            repository_with_events(outbox_event("idea.invalid.arguments.v1")),
            AcceptingPublisher(),
            limit=0,
        )


def test_run_outbox_delivery_once_rejects_non_positive_retry_limit() -> None:
    with pytest.raises(ValueError, match="max_retry_count must be positive"):
        run_outbox_delivery_once(
            repository_with_events(outbox_event("idea.invalid.arguments.v1")),
            AcceptingPublisher(),
            max_retry_count=0,
        )


@pytest.mark.parametrize(
    ("delivered_at_utc", "message"),
    [
        (datetime(2026, 6, 21, 10, 5), "delivered_at_utc must be timezone-aware"),
        (
            datetime(2026, 6, 21, 18, 5, tzinfo=timezone(timedelta(hours=8))),
            "delivered_at_utc must be UTC",
        ),
    ],
)
def test_run_outbox_delivery_once_requires_utc_delivery_time(
    delivered_at_utc: datetime,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_outbox_delivery_once(
            repository_with_events(outbox_event("idea.invalid-time.v1")),
            AcceptingPublisher(),
            delivered_at_utc=delivered_at_utc,
        )


def test_outbox_event_record_rejects_invalid_status_state() -> None:
    with pytest.raises(ValueError, match="retry_count cannot be negative"):
        invalid_outbox_event(retry_count=-1)
    with pytest.raises(ValueError, match="published_at_utc is required"):
        invalid_outbox_event(status=OutboxEventStatus.PUBLISHED)
    with pytest.raises(ValueError, match="failure_reason is required"):
        invalid_outbox_event(status=OutboxEventStatus.FAILED)
    with pytest.raises(ValueError, match="occurred_at_utc must be timezone-aware"):
        invalid_outbox_event(
            occurred_at_utc=datetime(2026, 6, 21, 10, 0),
        )
    with pytest.raises(ValueError, match="occurred_at_utc must be UTC"):
        invalid_outbox_event(
            occurred_at_utc=datetime(
                2026,
                6,
                21,
                18,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            ),
        )


def invalid_outbox_event(
    *,
    occurred_at_utc: datetime = EVENT_TIME,
    status: OutboxEventStatus = OutboxEventStatus.PENDING,
    retry_count: int = 0,
) -> OutboxEventRecord:
    return OutboxEventRecord(
        event_id="evt_invalid_state",
        event_type="idea.candidate.persisted.v1",
        aggregate_type="idea_candidate",
        aggregate_id="idea_high_cash_001",
        schema_version="v1",
        payload={"candidate_family": "high_cash"},
        occurred_at_utc=occurred_at_utc,
        status=status,
        retry_count=retry_count,
    )


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
