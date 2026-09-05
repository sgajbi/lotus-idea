from datetime import UTC, datetime
from typing import Any, cast

from app.domain import CandidatePresentationReceipt, InMemoryIdeaRepository
from app.runtime.repository_state import get_idea_repository


def record_workbench_presentation(candidate_id: str) -> dict[str, Any]:
    repository = cast(InMemoryIdeaRepository, get_idea_repository())
    record = repository.candidate_record_by_id(candidate_id)
    if record is None:
        return _missing_candidate_authority(candidate_id)
    candidate = record.candidate
    assert candidate.access_scope is not None
    assert candidate.score is not None
    receipt_id = f"receipt-{candidate_id}"
    repository.record_presentation_receipt(
        CandidatePresentationReceipt(
            receipt_id=receipt_id,
            candidate_id=candidate_id,
            tenant_id=candidate.access_scope.tenant_id,
            presented_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
            rank_at_presentation=1,
            visible_candidate_count=1,
            queue_snapshot_digest="sha256:" + "a" * 64,
            queue_policy_version="idea-review-queue-v1",
            ranking_policy_version=candidate.score.policy_version,
            candidate_material_version=candidate.identity.material_version,
            candidate_evidence_version=candidate.identity.evidence_version,
            accepted_at_utc=datetime(2026, 6, 21, 10, 15, tzinfo=UTC),
        )
    )
    return {
        "reviewChannel": "workbench",
        **exact_candidate_evidence_payload(candidate_id),
        "presentationReceiptId": receipt_id,
    }


def exact_candidate_evidence_payload(candidate_id: str) -> dict[str, Any]:
    repository = cast(InMemoryIdeaRepository, get_idea_repository())
    record = repository.candidate_record_by_id(candidate_id)
    if record is None:
        return _missing_candidate_authority(candidate_id)
    candidate = record.candidate
    return {
        "expectedMaterialVersion": candidate.identity.material_version,
        "expectedEvidenceVersion": candidate.identity.evidence_version,
        "expectedEvidencePacketId": candidate.evidence_packet.evidence_packet_id,
        "expectedEvidenceContentHash": candidate.evidence_packet.lineage_ref.content_hash,
    }


def exact_conversion_authority_payload(
    candidate_id: str,
    *,
    review_id: str | None = None,
) -> dict[str, Any]:
    repository = cast(InMemoryIdeaRepository, get_idea_repository())
    record = repository.candidate_record_by_id(candidate_id)
    effective_review_id = review_id
    if effective_review_id is None:
        if record is None or not record.review_decisions:
            raise AssertionError("conversion test candidate requires a persisted review")
        effective_review_id = record.review_decisions[-1].review_id
    return {
        "expectedReviewId": effective_review_id,
        **exact_candidate_evidence_payload(candidate_id),
    }


def _missing_candidate_authority(candidate_id: str) -> dict[str, Any]:
    return {
        "reviewChannel": "workbench",
        "expectedMaterialVersion": 1,
        "expectedEvidenceVersion": 1,
        "expectedEvidencePacketId": "missing-evidence-packet",
        "expectedEvidenceContentHash": "sha256:missing-evidence",
        "presentationReceiptId": f"receipt-{candidate_id}",
    }


__all__ = [
    "exact_candidate_evidence_payload",
    "exact_conversion_authority_payload",
    "record_workbench_presentation",
]
