from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from app.domain.ai_lineage_persistence import AIExplanationLineageRecord
from app.domain.audit import AuditEvent
from app.domain.conversion_governance import GovernedConversionIntent, GovernedConversionOutcome
from app.domain.downstream_submission import DownstreamSubmissionRecord
from app.domain.outbox.events import OutboxEventRecord
from app.domain.idempotency import IdempotencyRecord
from app.domain.ideas import IdeaCandidate, IdeaLifecycleStatus
from app.domain.report_evidence import GovernedReportEvidencePack
from app.domain.review_governance import GovernedFeedbackEvent, GovernedReviewDecision


class CandidatePersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    DUPLICATE_CANDIDATE = "duplicate_candidate"


class EvidenceReplayStatus(StrEnum):
    MATCHED = "matched"
    STALE_SOURCE = "stale_source"
    HASH_MISMATCH = "hash_mismatch"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"


class ReviewPersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    IDENTITY_CONFLICT = "identity_conflict"
    NOT_FOUND = "not_found"


class LifecyclePersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


class ConversionPersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    OUTCOME_CONFLICT = "outcome_conflict"
    NOT_FOUND = "not_found"


class EvidencePackPersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class LifecycleHistoryEntry:
    candidate_id: str
    source_status: IdeaLifecycleStatus
    target_status: IdeaLifecycleStatus
    actor_subject: str
    changed_at_utc: datetime

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.changed_at_utc, "changed_at_utc")


@dataclass(frozen=True)
class CandidatePersistenceRecord:
    candidate: IdeaCandidate
    evidence_hash: str
    persisted_at_utc: datetime
    lifecycle_history: tuple[LifecycleHistoryEntry, ...] = ()
    audit_events: tuple[AuditEvent, ...] = ()
    review_decisions: tuple[GovernedReviewDecision, ...] = ()
    feedback_events: tuple[GovernedFeedbackEvent, ...] = ()
    conversion_intents: tuple[GovernedConversionIntent, ...] = ()
    conversion_outcomes: tuple[GovernedConversionOutcome, ...] = ()
    report_evidence_packs: tuple[GovernedReportEvidencePack, ...] = ()
    ai_explanation_lineage_records: tuple[AIExplanationLineageRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.evidence_hash, "evidence_hash")
        _require_aware_utc(self.persisted_at_utc, "persisted_at_utc")
        object.__setattr__(self, "lifecycle_history", tuple(self.lifecycle_history))
        object.__setattr__(self, "audit_events", tuple(self.audit_events))
        object.__setattr__(self, "review_decisions", tuple(self.review_decisions))
        object.__setattr__(self, "feedback_events", tuple(self.feedback_events))
        object.__setattr__(self, "conversion_intents", tuple(self.conversion_intents))
        object.__setattr__(self, "conversion_outcomes", tuple(self.conversion_outcomes))
        object.__setattr__(self, "report_evidence_packs", tuple(self.report_evidence_packs))
        object.__setattr__(
            self,
            "ai_explanation_lineage_records",
            tuple(self.ai_explanation_lineage_records),
        )

    def is_expired_at(self, evaluated_at_utc: datetime) -> bool:
        _require_aware_utc(evaluated_at_utc, "evaluated_at_utc")
        return self.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED


@dataclass(frozen=True)
class CandidatePersistenceResult:
    decision: CandidatePersistenceDecision
    record: CandidatePersistenceRecord | None
    audit_event: AuditEvent | None = None


@dataclass(frozen=True)
class EvidenceReplayResult:
    status: EvidenceReplayStatus
    record: CandidatePersistenceRecord | None
    current_evidence_hash: str | None = None


@dataclass(frozen=True)
class ReviewPersistenceResult:
    decision: ReviewPersistenceDecision
    record: CandidatePersistenceRecord | None
    audit_event: AuditEvent | None = None


@dataclass(frozen=True)
class LifecyclePersistenceResult:
    decision: LifecyclePersistenceDecision
    record: CandidatePersistenceRecord | None
    audit_event: AuditEvent | None = None


@dataclass(frozen=True)
class ConversionPersistenceResult:
    decision: ConversionPersistenceDecision
    record: CandidatePersistenceRecord | None
    audit_event: AuditEvent | None = None


@dataclass(frozen=True)
class EvidencePackPersistenceResult:
    decision: EvidencePackPersistenceDecision
    record: CandidatePersistenceRecord | None
    audit_event: AuditEvent | None = None


@dataclass(frozen=True)
class IdeaRepositorySnapshot:
    candidate_records: Mapping[str, CandidatePersistenceRecord]
    idempotency_records: Mapping[str, IdempotencyRecord]
    idempotency_candidates: Mapping[str, str]
    conversion_intent_candidates: Mapping[str, str] = field(default_factory=dict)
    report_evidence_pack_candidates: Mapping[str, str] = field(default_factory=dict)
    ai_explanation_lineage_candidates: Mapping[str, str] = field(default_factory=dict)
    outbox_events: Mapping[str, OutboxEventRecord] = field(default_factory=dict)
    downstream_submission_records: Mapping[str, DownstreamSubmissionRecord] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidate_records", MappingProxyType(dict(self.candidate_records))
        )
        object.__setattr__(
            self,
            "idempotency_records",
            MappingProxyType(dict(self.idempotency_records)),
        )
        object.__setattr__(
            self,
            "idempotency_candidates",
            MappingProxyType(dict(self.idempotency_candidates)),
        )
        object.__setattr__(
            self,
            "conversion_intent_candidates",
            MappingProxyType(dict(self.conversion_intent_candidates)),
        )
        object.__setattr__(
            self,
            "report_evidence_pack_candidates",
            MappingProxyType(dict(self.report_evidence_pack_candidates)),
        )
        object.__setattr__(
            self,
            "ai_explanation_lineage_candidates",
            MappingProxyType(dict(self.ai_explanation_lineage_candidates)),
        )
        object.__setattr__(
            self,
            "outbox_events",
            MappingProxyType(dict(self.outbox_events)),
        )
        object.__setattr__(
            self,
            "downstream_submission_records",
            MappingProxyType(dict(self.downstream_submission_records)),
        )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
