from dataclasses import replace
from datetime import datetime, timedelta
from typing import Callable

from app.domain import (
    CandidateEvidenceIdentity,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewActionResult,
    ReviewAuthorityGrant,
    ReviewDecisionCommand,
    ReviewPosture,
    apply_review_action,
    request_conversion_intent,
)
from app.domain.conversion_governance import ConversionIntentCommand, ConversionIntentResult
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.support.review_authority import (
    presentation_receipt_for_candidate,
    review_authority_grant_for_candidate,
)


def conversion_with_exact_review_authority(
    candidate: IdeaCandidate,
    command: ConversionIntentCommand,
    *,
    accepted_at_utc: datetime,
) -> ConversionIntentResult:
    command = replace(
        command,
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate),
    )
    return request_conversion_intent(
        candidate,
        command,
        accepted_at_utc=accepted_at_utc,
        review_authority_grant=review_authority_grant_for_candidate(
            candidate,
            accepted_at_utc=accepted_at_utc - timedelta(minutes=1),
            review_id=command.expected_review_id,
        ),
    )


def review_with_exact_presentation(
    candidate: IdeaCandidate,
    command: ReviewDecisionCommand,
    *,
    accepted_at_utc: datetime,
) -> ReviewActionResult:
    command = replace(
        command,
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate),
    )
    receipt_id = command.presentation_receipt_id
    assert receipt_id is not None
    return apply_review_action(
        candidate,
        command,
        accepted_at_utc=accepted_at_utc,
        presentation_receipt=presentation_receipt_for_candidate(
            candidate,
            accepted_at_utc=accepted_at_utc,
            receipt_id=receipt_id,
        ),
    )


def persist_candidate_with_review_authority(
    repository: PostgresIdeaRepository,
    candidate: IdeaCandidate,
    *,
    idempotency_key: str,
    accepted_at_utc: datetime,
    review_command: Callable[[IdeaCandidate], ReviewDecisionCommand],
) -> tuple[IdeaCandidate, ReviewAuthorityGrant]:
    review_ready = replace(
        candidate,
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    )
    persisted = repository.persist_candidate(
        review_ready,
        idempotency_key=idempotency_key,
        payload={"candidateId": review_ready.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=accepted_at_utc,
    )
    assert persisted.record is not None
    review_result = review_with_exact_presentation(
        review_ready,
        review_command(review_ready),
        accepted_at_utc=accepted_at_utc,
    )
    review = repository.record_review_action(
        review_result,
        idempotency_key=f"{idempotency_key}:review",
        payload={"reviewId": review_result.decision.review_id},
    )
    assert review.record is not None
    grant = review_result.decision.authority_grant
    assert grant is not None
    return review.record.candidate, grant


__all__ = [
    "conversion_with_exact_review_authority",
    "persist_candidate_with_review_authority",
    "review_with_exact_presentation",
]
