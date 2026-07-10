from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.outbox_recovery import (
    OutboxRecoveryRunStatus,
    run_outbox_dead_letter_recovery,
)
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventStatus,
    build_candidate_outbox_event,
    mark_outbox_event_failed,
    outbox_dead_letter_support_reference,
)
from app.ports.outbox_publisher import OutboxPublishOutcome


EVENT_TIME = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


def test_recovery_publishes_once_and_replays_without_second_publication() -> None:
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    publisher = RecordingPublisher(accepted=True)
    request = _recovery_request(event.event_id, "recovery:application:001")

    first = run_outbox_dead_letter_recovery(repository, publisher, **request)
    replay = run_outbox_dead_letter_recovery(repository, publisher, **request)

    assert first.run_status is OutboxRecoveryRunStatus.PUBLISHED
    assert first.publication_attempted is True
    assert first.original_retry_count == 1
    assert replay.run_status is OutboxRecoveryRunStatus.REPLAYED
    assert replay.publication_attempted is False
    assert replay.recovery_reference == first.recovery_reference
    assert len(publisher.events) == 1
    published = repository.snapshot().outbox_events[event.event_id]
    assert published.status is OutboxEventStatus.PUBLISHED
    assert published.failure_reason == "publisher_rejected"
    assert published.first_failed_at_utc == event.first_failed_at_utc


def test_recovery_failure_returns_to_quarantine_without_automatic_retry() -> None:
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    publisher = RecordingPublisher(accepted=False)

    result = run_outbox_dead_letter_recovery(
        repository,
        publisher,
        **_recovery_request(event.event_id, "recovery:application:failure"),
    )

    assert result.run_status is OutboxRecoveryRunStatus.DEAD_LETTERED
    assert result.blocker == "publisher_rejected_again"
    recovered = repository.snapshot().outbox_events[event.event_id]
    assert recovered.status is OutboxEventStatus.DEAD_LETTER
    assert recovered.next_attempt_at_utc is None
    assert recovered.retry_count == 2
    assert recovered.first_failed_at_utc == event.first_failed_at_utc


def test_recovery_idempotency_conflict_never_publishes_twice() -> None:
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    publisher = RecordingPublisher(accepted=True)
    request = _recovery_request(event.event_id, "recovery:application:conflict")
    run_outbox_dead_letter_recovery(repository, publisher, **request)

    conflict = run_outbox_dead_letter_recovery(
        repository,
        publisher,
        **{**request, "reason": "different_approved_reason"},
    )

    assert conflict.run_status is OutboxRecoveryRunStatus.CONFLICT
    assert conflict.publication_attempted is False
    assert len(publisher.events) == 1


class RecordingPublisher:
    def __init__(self, *, accepted: bool) -> None:
        self.accepted = accepted
        self.events = []

    def publish(self, event):
        self.events.append(event)
        if self.accepted:
            return OutboxPublishOutcome.accepted_by_publisher()
        return OutboxPublishOutcome.rejected_by_publisher("publisher_rejected_again")


def _recovery_request(event_id: str, idempotency_key: str):
    return {
        "support_reference": outbox_dead_letter_support_reference(event_id),
        "idempotency_key": idempotency_key,
        "reason": "broker_route_corrected",
        "change_reference": "CHG-2026-0710",
        "actor_subject": "platform-operator",
        "requested_at_utc": EVENT_TIME + timedelta(minutes=5),
    }


def _dead_lettered_event():
    event = build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="candidate-sensitive",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
    )
    return mark_outbox_event_failed(
        event,
        failure_reason="publisher_rejected",
        failed_at_utc=EVENT_TIME + timedelta(minutes=1),
        max_retry_count=1,
        next_attempt_at_utc=None,
    )


def _repository_with_event(event):
    return InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={},
            report_evidence_pack_candidates={},
            ai_explanation_lineage_candidates={},
            outbox_events={event.event_id: event},
            downstream_submission_records={},
        )
    )
