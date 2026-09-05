from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.candidate_lookup import candidate_record_by_id
from app.application.persisted_action_evidence import (
    PersistedActionEvidenceUnavailable,
    require_single_persisted_action,
)
from app.domain import (
    DEFAULT_REVIEW_ACTION_POLICY,
    EventLineageContext,
    FeedbackCommand,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewActionPolicy,
    ReviewDecisionCommand,
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
    accepted_at_utc: datetime
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")


@dataclass(frozen=True)
class RecordFeedbackToRepositoryCommand:
    candidate_id: str
    feedback: FeedbackCommand
    idempotency_key: str
    accepted_at_utc: datetime
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")


@dataclass(frozen=True)
class ReviewWorkflowResult:
    review_decision: GovernedReviewDecision | None
    persistence: ReviewPersistenceResult

    def require_review_decision(self) -> GovernedReviewDecision:
        if self.review_decision is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful review mutation has no persisted review decision"
            )
        return self.review_decision


@dataclass(frozen=True)
class FeedbackWorkflowResult:
    feedback_event: GovernedFeedbackEvent | None
    persistence: ReviewPersistenceResult

    def require_feedback_event(self) -> GovernedFeedbackEvent:
        if self.feedback_event is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful feedback mutation has no persisted feedback event"
            )
        return self.feedback_event


def apply_review_action_to_repository(
    command: ApplyReviewActionToRepositoryCommand,
    *,
    repository: ReviewWorkflowRepository,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> ReviewWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return ReviewWorkflowResult(
            review_decision=None,
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
        return ReviewWorkflowResult(
            review_decision=_persisted_review_decision(command, prechecked),
            persistence=prechecked,
        )

    review_result = apply_review_action(
        record.candidate,
        command.review,
        accepted_at_utc=command.accepted_at_utc,
        policy=policy,
    )
    persistence = repository.record_review_action(
        review_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return ReviewWorkflowResult(
        review_decision=_persisted_review_decision(command, persistence),
        persistence=persistence,
    )


def record_feedback_to_repository(
    command: RecordFeedbackToRepositoryCommand,
    *,
    repository: ReviewWorkflowRepository,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> FeedbackWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return FeedbackWorkflowResult(
            feedback_event=None,
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
        return FeedbackWorkflowResult(
            feedback_event=_persisted_feedback_event(command, prechecked),
            persistence=prechecked,
        )

    feedback_result = record_feedback(
        record.candidate,
        command.feedback,
        accepted_at_utc=command.accepted_at_utc,
        policy=policy,
    )
    persistence = repository.record_feedback_event(
        feedback_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return FeedbackWorkflowResult(
        feedback_event=_persisted_feedback_event(command, persistence),
        persistence=persistence,
    )


def _persisted_review_decision(
    command: ApplyReviewActionToRepositoryCommand,
    persistence: ReviewPersistenceResult,
) -> GovernedReviewDecision | None:
    if persistence.decision not in {
        ReviewPersistenceDecision.ACCEPTED,
        ReviewPersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None or record.candidate.candidate_id != command.candidate_id:
        raise PersistedActionEvidenceUnavailable(
            "Successful review mutation has no matching candidate record"
        )
    expected_identity = review_mutation_identity_from_command(record.candidate, command.review)
    return require_single_persisted_action(
        decision
        for decision in record.review_decisions
        if decision.mutation_identity == expected_identity
    )


def _persisted_feedback_event(
    command: RecordFeedbackToRepositoryCommand,
    persistence: ReviewPersistenceResult,
) -> GovernedFeedbackEvent | None:
    if persistence.decision not in {
        ReviewPersistenceDecision.ACCEPTED,
        ReviewPersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None or record.candidate.candidate_id != command.candidate_id:
        raise PersistedActionEvidenceUnavailable(
            "Successful feedback mutation has no matching candidate record"
        )
    expected_identity = feedback_mutation_identity_from_command(record.candidate, command.feedback)
    return require_single_persisted_action(
        event for event in record.feedback_events if event.mutation_identity == expected_identity
    )


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
        "feedback_taxonomy_version": feedback.taxonomy_version,
        "outcome": feedback.outcome.value,
        "reason": feedback.reason.value,
        "recorded_at_utc": feedback.recorded_at_utc.isoformat(),
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if offset.total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")
