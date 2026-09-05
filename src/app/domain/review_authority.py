from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.domain.ideas import EvidenceSupportability, IdeaCandidate
from app.domain.presentation_receipts import CandidatePresentationReceipt
from app.domain.source_revision import (
    SOURCE_CUT_AUTHORITY_POLICY_VERSION,
    SourceCutPosture,
    source_cut_is_authoritative,
)


REVIEW_AUTHORITY_POLICY_VERSION = "idea-review-authority-v1"
WORKBENCH_REVIEW_WINDOW = timedelta(minutes=30)


class ReviewChannel(StrEnum):
    WORKBENCH = "workbench"
    OPERATOR = "operator"
    LEGACY_UNVERIFIED = "legacy_unverified"


class ReviewAuthorityStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ReviewAuthorityConflict(ValueError):
    code = "review_authority_conflict"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Review authority conflict: {reason}")
        self.reason = reason


@dataclass(frozen=True)
class CandidateEvidenceIdentity:
    candidate_id: str
    material_version: int
    evidence_version: int
    evidence_packet_id: str
    evidence_content_hash: str
    source_revision_vector_digest: str
    source_cut_posture: SourceCutPosture
    source_cut_authority_policy_version: str = SOURCE_CUT_AUTHORITY_POLICY_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "evidence_packet_id",
            "evidence_content_hash",
            "source_revision_vector_digest",
            "source_cut_authority_policy_version",
        ):
            _require_text(getattr(self, field_name), field_name)
        for field_name in ("material_version", "evidence_version"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")

    @classmethod
    def from_candidate(cls, candidate: IdeaCandidate) -> CandidateEvidenceIdentity:
        return cls(
            candidate_id=candidate.candidate_id,
            material_version=candidate.identity.material_version,
            evidence_version=candidate.identity.evidence_version,
            evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
            evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
            source_revision_vector_digest=(candidate.evidence_packet.source_revision_vector_digest),
            source_cut_posture=candidate.evidence_packet.source_cut_posture,
        )


@dataclass(frozen=True)
class ReviewAuthorityGrant:
    review_id: str
    candidate_evidence: CandidateEvidenceIdentity
    review_channel: ReviewChannel
    actor_subject: str
    actor_role: str
    review_policy_version: str
    accepted_at_utc: datetime
    applicability_expires_at_utc: datetime | None
    authority_policy_version: str = REVIEW_AUTHORITY_POLICY_VERSION
    presentation_receipt_id: str | None = None
    queue_snapshot_digest: str | None = None
    status: ReviewAuthorityStatus = ReviewAuthorityStatus.ACTIVE

    def __post_init__(self) -> None:
        for field_name in (
            "review_id",
            "actor_subject",
            "actor_role",
            "review_policy_version",
            "authority_policy_version",
        ):
            _require_text(getattr(self, field_name), field_name)
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")
        if self.applicability_expires_at_utc is not None:
            _require_aware_utc(
                self.applicability_expires_at_utc,
                "applicability_expires_at_utc",
            )
            if self.accepted_at_utc >= self.applicability_expires_at_utc:
                raise ValueError("review authority cannot be granted at or after expiry")
        presentation_values = (self.presentation_receipt_id, self.queue_snapshot_digest)
        if self.review_channel is ReviewChannel.WORKBENCH:
            if any(value is None for value in presentation_values):
                raise ValueError("Workbench review authority requires presentation context")
            for field_name in ("presentation_receipt_id", "queue_snapshot_digest"):
                value = getattr(self, field_name)
                assert value is not None
                _require_text(value, field_name)
        elif any(value is not None for value in presentation_values):
            raise ValueError("non-Workbench review authority cannot carry presentation context")

    def effective_status(
        self,
        candidate: IdeaCandidate,
        *,
        evaluated_at_utc: datetime,
    ) -> ReviewAuthorityStatus:
        _require_aware_utc(evaluated_at_utc, "evaluated_at_utc")
        if self.status is not ReviewAuthorityStatus.ACTIVE:
            return self.status
        if self.authority_policy_version != REVIEW_AUTHORITY_POLICY_VERSION:
            return ReviewAuthorityStatus.REVOKED
        if self.candidate_evidence != CandidateEvidenceIdentity.from_candidate(candidate):
            return ReviewAuthorityStatus.SUPERSEDED
        if not source_cut_is_authoritative(candidate.evidence_packet.source_cut_posture):
            return ReviewAuthorityStatus.REVOKED
        if candidate.evidence_packet.supportability is not EvidenceSupportability.READY:
            return ReviewAuthorityStatus.REVOKED
        if (
            self.applicability_expires_at_utc is not None
            and evaluated_at_utc >= self.applicability_expires_at_utc
        ):
            return ReviewAuthorityStatus.EXPIRED
        return ReviewAuthorityStatus.ACTIVE


def validate_expected_candidate_evidence(
    expected: CandidateEvidenceIdentity,
    candidate: IdeaCandidate,
) -> None:
    if expected != CandidateEvidenceIdentity.from_candidate(candidate):
        raise ReviewAuthorityConflict("candidate evidence identity is stale")


def validate_workbench_presentation(
    *,
    expected: CandidateEvidenceIdentity,
    receipt: CandidatePresentationReceipt,
    review_accepted_at_utc: datetime,
) -> None:
    _require_aware_utc(review_accepted_at_utc, "review_accepted_at_utc")
    if receipt.candidate_id != expected.candidate_id:
        raise ReviewAuthorityConflict("presentation candidate does not match")
    if receipt.candidate_material_version != expected.material_version:
        raise ReviewAuthorityConflict("presentation material version does not match")
    if receipt.candidate_evidence_version != expected.evidence_version:
        raise ReviewAuthorityConflict("presentation evidence version does not match")
    if receipt.accepted_at_utc > review_accepted_at_utc:
        raise ReviewAuthorityConflict("presentation was accepted after the review")
    if receipt.accepted_at_utc < review_accepted_at_utc - WORKBENCH_REVIEW_WINDOW:
        raise ReviewAuthorityConflict("presentation is outside the governed review window")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")


__all__ = [
    "REVIEW_AUTHORITY_POLICY_VERSION",
    "WORKBENCH_REVIEW_WINDOW",
    "CandidateEvidenceIdentity",
    "ReviewAuthorityConflict",
    "ReviewAuthorityGrant",
    "ReviewAuthorityStatus",
    "ReviewChannel",
    "validate_expected_candidate_evidence",
    "validate_workbench_presentation",
]
