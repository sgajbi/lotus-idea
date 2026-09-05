from app.domain import (
    InMemoryIdeaRepository,
    ReviewPersistenceDecision,
    apply_review_action,
    record_feedback,
)
from tests.unit.test_idea_persistence import (
    ACCEPTED_AT,
    EVALUATED_AT,
    feedback_command,
    review_decision_command,
    review_ready_high_cash_candidate,
)


def test_review_action_persistence_replays_conflicts_and_returns_not_found() -> None:
    candidate, refs = review_ready_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:review-ready:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = apply_review_action(
        persisted.record.candidate,
        review_decision_command(),
        accepted_at_utc=ACCEPTED_AT,
    )
    payload = {"review_id": result.decision.review_id, "action": result.decision.action.value}

    first = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload=payload,
    )
    replayed = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload=payload,
    )
    conflict = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload={"review_id": result.decision.review_id, "action": "reject"},
    )
    missing_candidate, _ = review_ready_high_cash_candidate()
    missing_result = apply_review_action(
        missing_candidate,
        review_decision_command(),
        accepted_at_utc=ACCEPTED_AT,
    )
    not_found = InMemoryIdeaRepository().record_review_action(
        missing_result,
        idempotency_key="review-action-key-missing",
        payload=payload,
    )

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.record == first.record
    assert conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.record == first.record
    assert not_found.decision is ReviewPersistenceDecision.NOT_FOUND
    assert not_found.record is None


def test_feedback_persistence_replays_conflicts_and_returns_not_found() -> None:
    candidate, refs = review_ready_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:feedback-ready:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = record_feedback(
        persisted.record.candidate,
        feedback_command(),
        accepted_at_utc=ACCEPTED_AT,
    )
    payload = {
        "feedback_id": result.feedback_event.feedback.feedback_id,
        "outcome": result.feedback_event.feedback.outcome.value,
    }

    first = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload=payload,
    )
    replayed = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload=payload,
    )
    conflict = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload={"feedback_id": result.feedback_event.feedback.feedback_id, "outcome": "ignored"},
    )
    missing_candidate, _ = review_ready_high_cash_candidate()
    missing_result = record_feedback(
        missing_candidate,
        feedback_command(),
        accepted_at_utc=ACCEPTED_AT,
    )
    not_found = InMemoryIdeaRepository().record_feedback_event(
        missing_result,
        idempotency_key="feedback-key-missing",
        payload=payload,
    )

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.record == first.record
    assert conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.record == first.record
    assert not_found.decision is ReviewPersistenceDecision.NOT_FOUND
    assert not_found.record is None
