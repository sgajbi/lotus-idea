from __future__ import annotations

from dataclasses import replace

from app.domain import IdeaLifecycleStatus, ReviewAction, apply_review_action, record_feedback
from app.domain.persistence import ReviewPersistenceDecision
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    feedback_command,
    high_cash_candidate,
    review_command,
)


def test_postgres_repository_reads_review_identity_collision_as_replay() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_review_identity_replay",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:review-identity-replay",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    review = apply_review_action(
        candidate,
        review_command(review_id="review-resource-identity-replay"),
    )

    first = repository.record_review_action(
        review,
        idempotency_key="review:resource-identity:first",
        payload={"reviewId": review.decision.review_id},
    )
    replayed = repository.record_review_action(
        review,
        idempotency_key="review:resource-identity:retry",
        payload={"reviewId": review.decision.review_id},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records[candidate.candidate_id]

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert connection.rollbacks == 0
    assert len(record.review_decisions) == 1
    assert len(record.audit_events) == 2
    assert len(recovered.outbox_events) == 2
    assert {
        row["idempotency_key"]
        for row in connection.rows["idea_idempotency_record"]
        if row["idempotency_key"].startswith("review:resource-identity:")
    } == {"review:resource-identity:first", "review:resource-identity:retry"}


def test_postgres_repository_reads_changed_review_identity_as_typed_conflict() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_review_identity_conflict",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:review-identity-conflict",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    review_id = "review-resource-identity-conflict"
    first_review = apply_review_action(candidate, review_command(review_id=review_id))
    changed_review = apply_review_action(
        candidate,
        replace(review_command(review_id=review_id), action=ReviewAction.REJECT),
    )

    first = repository.record_review_action(
        first_review,
        idempotency_key="review:resource-conflict:first",
        payload={"reviewId": review_id, "action": "approve_for_conversion"},
    )
    conflict = repository.record_review_action(
        changed_review,
        idempotency_key="review:resource-conflict:changed",
        payload={"reviewId": review_id, "action": "reject"},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records[candidate.candidate_id]

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert conflict.decision is ReviewPersistenceDecision.IDENTITY_CONFLICT
    assert connection.rollbacks == 0
    assert [decision.action for decision in record.review_decisions] == [
        ReviewAction.APPROVE_FOR_CONVERSION
    ]
    assert len(record.audit_events) == 2
    assert len(recovered.outbox_events) == 2
    assert not any(
        row["idempotency_key"] == "review:resource-conflict:changed"
        for row in connection.rows["idea_idempotency_record"]
    )


def test_postgres_repository_reads_feedback_identity_collision_as_replay() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_feedback_identity_replay",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:feedback-identity-replay",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    feedback = record_feedback(candidate, feedback_command())

    first = repository.record_feedback_event(
        feedback,
        idempotency_key="feedback:resource-identity:first",
        payload={"feedbackId": feedback.feedback_event.feedback.feedback_id},
    )
    replayed = repository.record_feedback_event(
        feedback,
        idempotency_key="feedback:resource-identity:retry",
        payload={"feedbackId": feedback.feedback_event.feedback.feedback_id},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records[candidate.candidate_id]

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert connection.rollbacks == 0
    assert len(record.feedback_events) == 1
    assert len(record.audit_events) == 2
    assert len(recovered.outbox_events) == 2
