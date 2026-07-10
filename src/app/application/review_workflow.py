from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.application.candidate_lookup import candidate_record_by_id
from app.domain import (
    DEFAULT_REVIEW_ACTION_POLICY,
    EventLineageContext,
    FeedbackCommand,
    FeedbackResult,
    ReviewAccessScope,
    ReviewActionPolicy,
    ReviewActionResult,
    ReviewDecisionCommand,
    ReviewEntitlementDenied,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
    apply_review_action,
    feedback_mutation_identity_from_command,
    record_feedback,
    review_mutation_identity_from_command,
)
from app.ports.idea_repository import ReviewWorkflowRepository


@dataclass(frozen=True)
class ApplyReviewActionToRepositoryCommand:
    candidate_id: str
    review: ReviewDecisionCommand
    idempotency_key: str
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class RecordFeedbackToRepositoryCommand:
    candidate_id: str
    feedback: FeedbackCommand
    idempotency_key: str
    event_lineage: EventLineageContext | None = None

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
    record = candidate_record_by_id(repository, command.candidate_id)
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
        identity=review_mutation_identity_from_command(record.candidate, command.review),
    )
    if prechecked is not None:
        return ReviewWorkflowResult(review_result=None, persistence=prechecked)

    review = replace(
        command.review,
        access_scope=_persisted_candidate_access_scope(
            candidate_id=record.candidate.candidate_id,
            access_scope=record.candidate.access_scope,
        ),
    )
    review_result = apply_review_action(record.candidate, review, policy=policy)
    persistence = repository.record_review_action(
        review_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return ReviewWorkflowResult(review_result=review_result, persistence=persistence)


def record_feedback_to_repository(
    command: RecordFeedbackToRepositoryCommand,
    *,
    repository: ReviewWorkflowRepository,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> FeedbackWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
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
        identity=feedback_mutation_identity_from_command(record.candidate, command.feedback),
    )
    if prechecked is not None:
        return FeedbackWorkflowResult(feedback_result=None, persistence=prechecked)

    feedback = replace(
        command.feedback,
        access_scope=_persisted_candidate_access_scope(
            candidate_id=record.candidate.candidate_id,
            access_scope=record.candidate.access_scope,
        ),
    )
    feedback_result = record_feedback(record.candidate, feedback, policy=policy)
    persistence = repository.record_feedback_event(
        feedback_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return FeedbackWorkflowResult(feedback_result=feedback_result, persistence=persistence)


def _review_payload(command: ApplyReviewActionToRepositoryCommand) -> dict[str, Any]:
    review = command.review
    return {
        "action": review.action.value,
        "actor_role": review.actor.role.value,
        "actor_subject": review.actor.actor_subject,
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
        "actor_subject": feedback.actor.actor_subject,
        "candidate_id": command.candidate_id,
        "feedback_id": feedback.feedback_id,
        "outcome": feedback.outcome.value,
        "reason_codes": [reason.value for reason in feedback.reason_codes],
        "recorded_at_utc": feedback.recorded_at_utc.isoformat(),
    }


def _persisted_candidate_access_scope(
    candidate_id: str,
    access_scope: ReviewAccessScope | None,
) -> ReviewAccessScope:
    if access_scope is None:
        raise ReviewEntitlementDenied(candidate_id)
    return access_scope


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
