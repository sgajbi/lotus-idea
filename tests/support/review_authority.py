from dataclasses import replace
from datetime import datetime

from app.domain import (
    CandidateEvidenceIdentity,
    CandidatePresentationReceipt,
    ConversionIntentCommand,
    ConversionIntentResult,
    GovernedReviewDecision,
    IdeaCandidate,
    InMemoryIdeaRepository,
    ReviewAuthorityGrant,
    ReviewAction,
    ReviewActorRole,
    ReviewChannel,
    ReviewPosture,
    ReasonCode,
    request_conversion_intent,
)


def presentation_receipt_for_candidate(
    candidate: IdeaCandidate,
    *,
    accepted_at_utc: datetime,
    receipt_id: str = "receipt-review-test-001",
) -> CandidatePresentationReceipt:
    scope = candidate.access_scope
    if scope is None:
        raise ValueError("review-authority test candidate requires access scope")
    return CandidatePresentationReceipt(
        receipt_id=receipt_id,
        candidate_id=candidate.candidate_id,
        tenant_id=scope.tenant_id,
        presented_at_utc=accepted_at_utc,
        rank_at_presentation=1,
        visible_candidate_count=1,
        queue_snapshot_digest="sha256:" + "a" * 64,
        queue_policy_version="idea-review-queue-v1",
        ranking_policy_version=(
            candidate.score.policy_version if candidate.score is not None else "unranked-test"
        ),
        candidate_material_version=candidate.identity.material_version,
        candidate_evidence_version=candidate.identity.evidence_version,
        accepted_at_utc=accepted_at_utc,
    )


def evidence_identity_for_candidate(candidate: IdeaCandidate) -> CandidateEvidenceIdentity:
    return CandidateEvidenceIdentity.from_candidate(candidate)


def review_authority_grant_for_candidate(
    candidate: IdeaCandidate,
    *,
    accepted_at_utc: datetime,
    review_id: str = "review-authority-test-001",
) -> ReviewAuthorityGrant:
    return ReviewAuthorityGrant(
        review_id=review_id,
        candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate),
        review_channel=ReviewChannel.WORKBENCH,
        actor_subject="advisor-001",
        actor_role="advisor",
        review_policy_version="idea-human-review-v1",
        accepted_at_utc=accepted_at_utc,
        applicability_expires_at_utc=(
            candidate.evidence_packet.applicability_expires_at_utc
        ),
        presentation_receipt_id="receipt-review-test-001",
        queue_snapshot_digest="sha256:" + "a" * 64,
    )


def approved_review_decision_for_candidate(
    candidate: IdeaCandidate,
    *,
    accepted_at_utc: datetime,
    review_id: str = "review-authority-test-001",
) -> GovernedReviewDecision:
    grant = review_authority_grant_for_candidate(
        candidate,
        accepted_at_utc=accepted_at_utc,
        review_id=review_id,
    )
    return GovernedReviewDecision(
        review_id=grant.review_id,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=grant.candidate_evidence.evidence_packet_id,
        evidence_content_hash=grant.candidate_evidence.evidence_content_hash,
        candidate_material_version=grant.candidate_evidence.material_version,
        candidate_evidence_version=grant.candidate_evidence.evidence_version,
        review_channel=grant.review_channel,
        presentation_receipt_id=grant.presentation_receipt_id,
        queue_snapshot_digest=grant.queue_snapshot_digest,
        review_policy_version=grant.review_policy_version,
        review_authority_policy_version=grant.authority_policy_version,
        action=ReviewAction.APPROVE_FOR_CONVERSION,
        resulting_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        actor_subject=grant.actor_subject,
        actor_role=ReviewActorRole.ADVISOR,
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        decided_at_utc=accepted_at_utc,
        accepted_at_utc=accepted_at_utc,
        applicability_expires_at_utc=grant.applicability_expires_at_utc,
    )


def conversion_intent_result_for_candidate(
    candidate: IdeaCandidate,
    command: ConversionIntentCommand,
    *,
    accepted_at_utc: datetime,
    review_accepted_at_utc: datetime,
) -> ConversionIntentResult:
    return request_conversion_intent(
        candidate,
        command,
        accepted_at_utc=accepted_at_utc,
        review_authority_grant=review_authority_grant_for_candidate(
            candidate,
            accepted_at_utc=review_accepted_at_utc,
            review_id=command.expected_review_id,
        ),
    )


def with_in_memory_review_authority(
    repository: InMemoryIdeaRepository,
    candidate: IdeaCandidate,
    *,
    accepted_at_utc: datetime,
    review_id: str = "review-authority-test-001",
) -> InMemoryIdeaRepository:
    snapshot = repository.snapshot()
    record = snapshot.candidate_records[candidate.candidate_id]
    reviewed_record = replace(
        record,
        review_decisions=(
            *record.review_decisions,
            approved_review_decision_for_candidate(
                candidate,
                accepted_at_utc=accepted_at_utc,
                review_id=review_id,
            ),
        ),
    )
    return InMemoryIdeaRepository(
        replace(
            snapshot,
            candidate_records={
                **snapshot.candidate_records,
                candidate.candidate_id: reviewed_record,
            },
        )
    )
__all__ = [
    "evidence_identity_for_candidate",
    "approved_review_decision_for_candidate",
    "conversion_intent_result_for_candidate",
    "presentation_receipt_for_candidate",
    "review_authority_grant_for_candidate",
    "with_in_memory_review_authority",
]
