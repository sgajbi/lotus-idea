from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain import (
    DEFAULT_REVIEW_ACTION_POLICY,
    FeedbackCommand,
    FeedbackResult,
    IdeaRepositorySnapshot,
    ReviewActionPolicy,
    ReviewActionResult,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
    apply_review_action,
    record_feedback,
)


class ReviewWorkflowRepository(Protocol):
    def snapshot(self) -> IdeaRepositorySnapshot: ...

    def precheck_review_mutation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult | None: ...

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult: ...

    def record_feedback_event(
        self,
        result: FeedbackResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult: ...


@dataclass(frozen=True)
class ApplyReviewActionToRepositoryCommand:
    candidate_id: str
    review: ReviewDecisionCommand
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class RecordFeedbackToRepositoryCommand:
    candidate_id: str
    feedback: FeedbackCommand
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class ReviewWorkflowResult:
    review_result: ReviewActionResult | None
    persistence: ReviewPersistenceResult


@dataclass(frozen=True)
class FeedbackWorkflowResult:
    feedback_result: FeedbackResult | None
    persistence: ReviewPersistenceResult


def apply_review_action_to_repository(
    command: ApplyReviewActionToRepositoryCommand,
    *,
    repository: ReviewWorkflowRepository,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> ReviewWorkflowResult:
    snapshot = repository.snapshot()
    record = snapshot.candidate_records.get(command.candidate_id)
    if record is None:
        return ReviewWorkflowResult(
            review_result=None,
            persistence=ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    payload = _review_payload(command)
    prechecked = repository.precheck_review_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return ReviewWorkflowResult(review_result=None, persistence=prechecked)

    review_result = apply_review_action(record.candidate, command.review, policy=policy)
    persistence = repository.record_review_action(
        review_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    return ReviewWorkflowResult(review_result=review_result, persistence=persistence)


def record_feedback_to_repository(
    command: RecordFeedbackToRepositoryCommand,
    *,
    repository: ReviewWorkflowRepository,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> FeedbackWorkflowResult:
    snapshot = repository.snapshot()
    record = snapshot.candidate_records.get(command.candidate_id)
    if record is None:
        return FeedbackWorkflowResult(
            feedback_result=None,
            persistence=ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    payload = _feedback_payload(command)
    prechecked = repository.precheck_review_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return FeedbackWorkflowResult(feedback_result=None, persistence=prechecked)

    feedback_result = record_feedback(record.candidate, command.feedback, policy=policy)
    persistence = repository.record_feedback_event(
        feedback_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    return FeedbackWorkflowResult(feedback_result=feedback_result, persistence=persistence)


def _review_payload(command: ApplyReviewActionToRepositoryCommand) -> dict[str, Any]:
    review = command.review
    return {
        "action": review.action.value,
        "actor_role": review.actor.role.value,
        "candidate_id": command.candidate_id,
        "decided_at_utc": review.decided_at_utc.isoformat(),
        "reason_codes": [reason.value for reason in review.reason_codes],
        "review_id": review.review_id,
        "snoozed_until_utc": (
            review.snoozed_until_utc.isoformat() if review.snoozed_until_utc is not None else None
        ),
        "suppression_reason": (
            review.suppression_reason.value if review.suppression_reason is not None else None
        ),
    }


def _feedback_payload(command: RecordFeedbackToRepositoryCommand) -> dict[str, Any]:
    feedback = command.feedback
    return {
        "actor_role": feedback.actor.role.value,
        "candidate_id": command.candidate_id,
        "feedback_id": feedback.feedback_id,
        "outcome": feedback.outcome.value,
        "reason_codes": [reason.value for reason in feedback.reason_codes],
        "recorded_at_utc": feedback.recorded_at_utc.isoformat(),
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
