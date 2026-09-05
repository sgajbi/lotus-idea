from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Any

from app.domain.control_time import (
    PRESENTATION_TIME_POLICY,
    AcceptanceTimeSource,
    require_observed_time_within_policy,
)
from app.domain.ideas import IdeaCandidate
from app.domain.source_revision import SourceCutPosture


PRESENTATION_RECEIPT_SCHEMA_VERSION = "lotus-idea.candidate-presentation-receipt.v2"
LEGACY_PRESENTATION_RECEIPT_SCHEMA_VERSION = "lotus-idea.candidate-presentation-receipt.v1"
PRESENTATION_SURFACE = "advisor_review_queue"
PRESENTATION_PRODUCER = "lotus-workbench"
MAX_PRESENTED_CANDIDATE_COUNT = 100
_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$")
_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class PresentationReceiptDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class CandidatePresentationReceipt:
    receipt_id: str
    candidate_id: str
    tenant_id: str
    presented_at_utc: datetime
    rank_at_presentation: int
    visible_candidate_count: int
    queue_snapshot_digest: str
    queue_policy_version: str
    ranking_policy_version: str
    candidate_material_version: int
    candidate_evidence_version: int
    source_revision_vector_digest: str | None
    source_cut_posture: SourceCutPosture
    accepted_at_utc: datetime
    acceptance_time_source: AcceptanceTimeSource = AcceptanceTimeSource.SERVER_ACCEPTED
    schema_version: str = PRESENTATION_RECEIPT_SCHEMA_VERSION
    surface: str = PRESENTATION_SURFACE
    producer: str = PRESENTATION_PRODUCER

    def __post_init__(self) -> None:
        for field_name in (
            "receipt_id",
            "candidate_id",
            "tenant_id",
            "queue_policy_version",
            "ranking_policy_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be a governed reference")
            if _REFERENCE_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{field_name} must be a governed reference")
        if self.schema_version not in {
            PRESENTATION_RECEIPT_SCHEMA_VERSION,
            LEGACY_PRESENTATION_RECEIPT_SCHEMA_VERSION,
        }:
            raise ValueError("unsupported presentation receipt schema_version")
        if self.surface != PRESENTATION_SURFACE:
            raise ValueError("unsupported presentation receipt surface")
        if self.producer != PRESENTATION_PRODUCER:
            raise ValueError("unsupported presentation receipt producer")
        if not isinstance(self.presented_at_utc, datetime):
            raise ValueError("presented_at_utc must be a datetime")
        if self.presented_at_utc.tzinfo is None or self.presented_at_utc.utcoffset() is None:
            raise ValueError("presented_at_utc must be timezone-aware")
        if self.presented_at_utc.utcoffset() != UTC.utcoffset(self.presented_at_utc):
            raise ValueError("presented_at_utc must be UTC")
        if not isinstance(self.accepted_at_utc, datetime):
            raise ValueError("accepted_at_utc must be a datetime")
        if self.accepted_at_utc.tzinfo is None or self.accepted_at_utc.utcoffset() is None:
            raise ValueError("accepted_at_utc must be timezone-aware")
        if self.accepted_at_utc.utcoffset() != UTC.utcoffset(self.accepted_at_utc):
            raise ValueError("accepted_at_utc must be UTC")
        if not _is_integer(self.visible_candidate_count) or not (
            1 <= self.visible_candidate_count <= MAX_PRESENTED_CANDIDATE_COUNT
        ):
            raise ValueError(
                f"visible_candidate_count must be between 1 and {MAX_PRESENTED_CANDIDATE_COUNT}"
            )
        if not _is_integer(self.rank_at_presentation) or self.rank_at_presentation <= 0:
            raise ValueError("rank_at_presentation must be a positive integer")
        if not isinstance(self.queue_snapshot_digest, str) or (
            _DIGEST_PATTERN.fullmatch(self.queue_snapshot_digest) is None
        ):
            raise ValueError("queue_snapshot_digest must be a sha256 digest")
        if self.schema_version == PRESENTATION_RECEIPT_SCHEMA_VERSION:
            if not isinstance(self.source_revision_vector_digest, str) or (
                _DIGEST_PATTERN.fullmatch(self.source_revision_vector_digest) is None
            ):
                raise ValueError("source_revision_vector_digest must be a sha256 digest")
        elif self.source_revision_vector_digest is not None:
            raise ValueError("legacy presentation receipts cannot claim a revision vector")
        if not isinstance(self.source_cut_posture, SourceCutPosture):
            raise ValueError("source_cut_posture must be a governed posture")
        if (
            self.schema_version == LEGACY_PRESENTATION_RECEIPT_SCHEMA_VERSION
            and self.source_cut_posture is not SourceCutPosture.UNKNOWN
        ):
            raise ValueError("legacy presentation receipts must retain unknown source cut posture")
        for field_name in ("candidate_material_version", "candidate_evidence_version"):
            value = getattr(self, field_name)
            if not _is_integer(value) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")

    def has_same_producer_claim(self, other: CandidatePresentationReceipt) -> bool:
        """Compare immutable producer evidence without server admission metadata."""

        return (
            self.receipt_id,
            self.candidate_id,
            self.tenant_id,
            self.presented_at_utc,
            self.rank_at_presentation,
            self.visible_candidate_count,
            self.queue_snapshot_digest,
            self.queue_policy_version,
            self.ranking_policy_version,
            self.candidate_material_version,
            self.candidate_evidence_version,
            self.source_revision_vector_digest,
            self.source_cut_posture,
            self.schema_version,
            self.surface,
            self.producer,
        ) == (
            other.receipt_id,
            other.candidate_id,
            other.tenant_id,
            other.presented_at_utc,
            other.rank_at_presentation,
            other.visible_candidate_count,
            other.queue_snapshot_digest,
            other.queue_policy_version,
            other.ranking_policy_version,
            other.candidate_material_version,
            other.candidate_evidence_version,
            other.source_revision_vector_digest,
            other.source_cut_posture,
            other.schema_version,
            other.surface,
            other.producer,
        )


@dataclass(frozen=True)
class PresentationReceiptResult:
    decision: PresentationReceiptDecision
    receipt: CandidatePresentationReceipt | None


class PresentationReceiptCandidateStateError(RuntimeError):
    """The candidate no longer matches the immutable presentation claim."""


def validate_presentation_receipt_candidate(
    receipt: CandidatePresentationReceipt,
    candidate: IdeaCandidate,
) -> None:
    require_observed_time_within_policy(
        receipt.presented_at_utc,
        receipt.accepted_at_utc,
        PRESENTATION_TIME_POLICY,
    )
    if receipt.candidate_id != candidate.candidate_id:
        raise PresentationReceiptCandidateStateError("candidate identity does not match receipt")
    if candidate.access_scope is None or receipt.tenant_id != candidate.access_scope.tenant_id:
        raise PresentationReceiptCandidateStateError("candidate tenant does not match receipt")
    if receipt.candidate_material_version != candidate.identity.material_version:
        raise PresentationReceiptCandidateStateError("candidate material version does not match")
    if receipt.candidate_evidence_version != candidate.identity.evidence_version:
        raise PresentationReceiptCandidateStateError("candidate evidence version does not match")
    if (
        receipt.source_revision_vector_digest
        != candidate.evidence_packet.source_revision_vector_digest
    ):
        raise PresentationReceiptCandidateStateError(
            "candidate source revision vector does not match receipt"
        )
    if receipt.source_cut_posture is not candidate.evidence_packet.source_cut_posture:
        raise PresentationReceiptCandidateStateError("candidate source cut posture does not match")
    if receipt.accepted_at_utc < candidate.updated_at_utc:
        raise PresentationReceiptCandidateStateError(
            "presentation acceptance predates the referenced candidate version"
        )


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


__all__ = [
    "MAX_PRESENTED_CANDIDATE_COUNT",
    "LEGACY_PRESENTATION_RECEIPT_SCHEMA_VERSION",
    "PRESENTATION_PRODUCER",
    "PRESENTATION_RECEIPT_SCHEMA_VERSION",
    "PRESENTATION_SURFACE",
    "CandidatePresentationReceipt",
    "PresentationReceiptCandidateStateError",
    "PresentationReceiptDecision",
    "PresentationReceiptResult",
    "validate_presentation_receipt_candidate",
]
