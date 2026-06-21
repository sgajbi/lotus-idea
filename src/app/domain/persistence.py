from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from app.domain.audit import AuditEvent
from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord, evaluate_idempotency
from app.domain.ideas import (
    EvidenceFreshness,
    IdeaCandidate,
    IdeaLifecycleStatus,
    SourceRef,
    transition_candidate,
)
from app.domain.conversion_governance import (
    ConversionIntentResult,
    ConversionOutcomeResult,
    GovernedConversionIntent,
    GovernedConversionOutcome,
)
from app.domain.report_evidence import (
    GovernedReportEvidencePack,
    ReportEvidencePackResult,
)
from app.domain.review_governance import (
    FeedbackResult,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewActionResult,
)


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


class InMemoryIdeaRepository:
    """Internal persistence contract for RFC-0002 Slice 06 before a database adapter exists."""

    def __init__(self, snapshot: IdeaRepositorySnapshot | None = None) -> None:
        self._candidate_records: dict[str, CandidatePersistenceRecord] = {}
        self._idempotency_records: dict[str, IdempotencyRecord] = {}
        self._idempotency_candidates: dict[str, str] = {}
        self._conversion_intent_candidates: dict[str, str] = {}
        self._report_evidence_pack_candidates: dict[str, str] = {}
        if snapshot is not None:
            self._candidate_records.update(snapshot.candidate_records)
            self._idempotency_records.update(snapshot.idempotency_records)
            self._idempotency_candidates.update(snapshot.idempotency_candidates)
            self._conversion_intent_candidates.update(snapshot.conversion_intent_candidates)
            self._report_evidence_pack_candidates.update(snapshot.report_evidence_pack_candidates)

    def persist_candidate(
        self,
        candidate: IdeaCandidate,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
    ) -> CandidatePersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        _require_text(actor_subject, "actor_subject")
        event_time = occurred_at_utc or datetime.now(UTC)
        _require_aware_utc(event_time, "occurred_at_utc")

        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return CandidatePersistenceResult(
                decision=CandidatePersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return CandidatePersistenceResult(
                decision=CandidatePersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if candidate.candidate_id in self._candidate_records:
            return CandidatePersistenceResult(
                decision=CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
                record=self._candidate_records[candidate.candidate_id],
            )

        audit_event = _audit_event(
            event_type="idea.candidate.persisted",
            actor_subject=actor_subject,
            outcome="accepted",
            occurred_at_utc=event_time,
            attributes={
                "candidate_family": candidate.family.value,
                "lifecycle_status": candidate.lifecycle_status.value,
                "idempotency_decision": idempotency_decision.value,
            },
        )
        record = CandidatePersistenceRecord(
            candidate=candidate,
            evidence_hash=evidence_hash_for_candidate(candidate),
            persisted_at_utc=event_time,
            audit_events=(audit_event,),
        )
        self._candidate_records[candidate.candidate_id] = record
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate.candidate_id
        return CandidatePersistenceResult(
            decision=CandidatePersistenceDecision.ACCEPTED,
            record=record,
            audit_event=audit_event,
        )

    def transition_candidate(
        self,
        candidate_id: str,
        target_status: IdeaLifecycleStatus,
        *,
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
    ) -> CandidatePersistenceRecord:
        _require_text(candidate_id, "candidate_id")
        _require_text(actor_subject, "actor_subject")
        event_time = occurred_at_utc or datetime.now(UTC)
        _require_aware_utc(event_time, "occurred_at_utc")
        record = self._candidate_records[candidate_id]
        updated, _ = self._transition_record(
            record,
            target_status=target_status,
            actor_subject=actor_subject,
            occurred_at_utc=event_time,
            attributes={},
        )
        return updated

    def record_lifecycle_transition(
        self,
        candidate_id: str,
        target_status: IdeaLifecycleStatus,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
        transition_id: str | None = None,
        reason_codes: tuple[str, ...] = (),
    ) -> LifecyclePersistenceResult:
        _require_text(candidate_id, "candidate_id")
        _require_text(idempotency_key, "idempotency_key")
        _require_text(actor_subject, "actor_subject")
        if transition_id is not None:
            _require_text(transition_id, "transition_id")
        event_time = occurred_at_utc or datetime.now(UTC)
        _require_aware_utc(event_time, "occurred_at_utc")

        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return LifecyclePersistenceResult(
                decision=LifecyclePersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return LifecyclePersistenceResult(
                decision=LifecyclePersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        record = self._candidate_records.get(candidate_id)
        if record is None:
            return LifecyclePersistenceResult(
                decision=LifecyclePersistenceDecision.NOT_FOUND,
                record=None,
            )

        attributes = {
            "idempotency_decision": idempotency_decision.value,
            "reason_codes": ",".join(reason_codes),
        }
        if transition_id is not None:
            attributes["transition_id"] = transition_id
        updated, audit_event = self._transition_record(
            record,
            target_status=target_status,
            actor_subject=actor_subject,
            occurred_at_utc=event_time,
            attributes=attributes,
        )
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        return LifecyclePersistenceResult(
            decision=LifecyclePersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=audit_event,
        )

    def replay_evidence(
        self,
        candidate_id: str,
        *,
        current_source_refs: tuple[SourceRef, ...],
        evaluated_at_utc: datetime | None = None,
    ) -> EvidenceReplayResult:
        _require_text(candidate_id, "candidate_id")
        event_time = evaluated_at_utc or datetime.now(UTC)
        _require_aware_utc(event_time, "evaluated_at_utc")
        record = self._candidate_records.get(candidate_id)
        if record is None:
            return EvidenceReplayResult(status=EvidenceReplayStatus.NOT_FOUND, record=None)
        if record.is_expired_at(event_time):
            return EvidenceReplayResult(status=EvidenceReplayStatus.EXPIRED, record=record)
        if any(
            source_ref.freshness is not EvidenceFreshness.CURRENT
            for source_ref in current_source_refs
        ):
            return EvidenceReplayResult(status=EvidenceReplayStatus.STALE_SOURCE, record=record)

        current_hash = evidence_hash_for_source_refs(current_source_refs)
        if current_hash == evidence_hash_for_source_refs(
            record.candidate.evidence_packet.source_refs
        ):
            return EvidenceReplayResult(
                status=EvidenceReplayStatus.MATCHED,
                record=record,
                current_evidence_hash=record.evidence_hash,
            )
        return EvidenceReplayResult(
            status=EvidenceReplayStatus.HASH_MISMATCH,
            record=record,
            current_evidence_hash=current_hash,
        )

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        candidate_id = result.decision.candidate_id
        _require_text(candidate_id, "candidate_id")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        record = self._candidate_records.get(candidate_id)
        if record is None:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.NOT_FOUND,
                record=None,
            )

        history = record.lifecycle_history
        if record.candidate.lifecycle_status is not result.candidate.lifecycle_status:
            history = (
                *history,
                LifecycleHistoryEntry(
                    candidate_id=candidate_id,
                    source_status=record.candidate.lifecycle_status,
                    target_status=result.candidate.lifecycle_status,
                    actor_subject=result.decision.actor_subject,
                    changed_at_utc=result.decision.decided_at_utc,
                ),
            )
        updated = replace(
            record,
            candidate=result.candidate,
            lifecycle_history=history,
            audit_events=(*record.audit_events, result.audit_event),
            review_decisions=(*record.review_decisions, result.decision),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def precheck_review_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult | None:
        _require_text(idempotency_key, "idempotency_key")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        if existing_idempotency is None:
            return None
        idempotency_decision, _ = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.REPLAYED,
            record=self._record_for_idempotency_key(idempotency_key),
        )

    def record_feedback_event(
        self,
        result: FeedbackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        candidate_id = result.feedback_event.candidate_id
        _require_text(candidate_id, "candidate_id")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        record = self._candidate_records.get(candidate_id)
        if record is None:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.NOT_FOUND,
                record=None,
            )

        updated = replace(
            record,
            audit_events=(*record.audit_events, result.audit_event),
            feedback_events=(*record.feedback_events, result.feedback_event),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def precheck_conversion_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult | None:
        _require_text(idempotency_key, "idempotency_key")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        if existing_idempotency is None:
            return None
        idempotency_decision, _ = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.REPLAYED,
            record=self._record_for_idempotency_key(idempotency_key),
        )

    def record_conversion_intent(
        self,
        result: ConversionIntentResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        candidate_id = result.conversion_intent.intent.candidate_id
        _require_text(candidate_id, "candidate_id")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        record = self._candidate_records.get(candidate_id)
        if record is None:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            )

        history = record.lifecycle_history
        if record.candidate.lifecycle_status is not result.candidate.lifecycle_status:
            history = (
                *history,
                LifecycleHistoryEntry(
                    candidate_id=candidate_id,
                    source_status=record.candidate.lifecycle_status,
                    target_status=result.candidate.lifecycle_status,
                    actor_subject=result.conversion_intent.actor_subject,
                    changed_at_utc=result.conversion_intent.intent.requested_at_utc,
                ),
            )
        updated = replace(
            record,
            candidate=result.candidate,
            lifecycle_history=history,
            audit_events=(*record.audit_events, result.audit_event),
            conversion_intents=(*record.conversion_intents, result.conversion_intent),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        self._conversion_intent_candidates[result.conversion_intent.intent.conversion_intent_id] = (
            candidate_id
        )
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None:
        _require_text(conversion_intent_id, "conversion_intent_id")
        candidate_id = self._conversion_intent_candidates.get(conversion_intent_id)
        if candidate_id is None:
            return None
        record = self._candidate_records.get(candidate_id)
        if record is None:
            return None
        for conversion_intent in record.conversion_intents:
            if conversion_intent.intent.conversion_intent_id == conversion_intent_id:
                return conversion_intent
        return None

    def record_conversion_outcome(
        self,
        result: ConversionOutcomeResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        conversion_intent_id = result.conversion_outcome.conversion_intent_id
        _require_text(conversion_intent_id, "conversion_intent_id")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        candidate_id = self._conversion_intent_candidates.get(conversion_intent_id)
        if candidate_id is None:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            )
        record = self._candidate_records.get(candidate_id)
        if record is None:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            )

        updated = replace(
            record,
            audit_events=(*record.audit_events, result.audit_event),
            conversion_outcomes=(*record.conversion_outcomes, result.conversion_outcome),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def precheck_evidence_pack_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> EvidencePackPersistenceResult | None:
        _require_text(idempotency_key, "idempotency_key")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        if existing_idempotency is None:
            return None
        idempotency_decision, _ = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        return EvidencePackPersistenceResult(
            decision=EvidencePackPersistenceDecision.REPLAYED,
            record=self._record_for_idempotency_key(idempotency_key),
        )

    def candidate_record_for_conversion_intent(
        self,
        conversion_intent_id: str,
    ) -> CandidatePersistenceRecord | None:
        _require_text(conversion_intent_id, "conversion_intent_id")
        candidate_id = self._conversion_intent_candidates.get(conversion_intent_id)
        if candidate_id is None:
            return None
        return self._candidate_records.get(candidate_id)

    def record_report_evidence_pack(
        self,
        result: ReportEvidencePackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> EvidencePackPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        candidate_id = result.evidence_pack.candidate_id
        _require_text(candidate_id, "candidate_id")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.CONFLICT,
                record=self._record_for_idempotency_key(idempotency_key),
            )
        if idempotency_decision is IdempotencyDecision.REPLAYED:
            return EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.REPLAYED,
                record=self._record_for_idempotency_key(idempotency_key),
            )

        record = self._candidate_records.get(candidate_id)
        if record is None:
            return EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.NOT_FOUND,
                record=None,
            )

        updated = replace(
            record,
            audit_events=(*record.audit_events, result.audit_event),
            report_evidence_packs=(*record.report_evidence_packs, result.evidence_pack),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        self._report_evidence_pack_candidates[result.evidence_pack.report_evidence_pack_id] = (
            candidate_id
        )
        return EvidencePackPersistenceResult(
            decision=EvidencePackPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def snapshot(self) -> IdeaRepositorySnapshot:
        return IdeaRepositorySnapshot(
            candidate_records=self._candidate_records,
            idempotency_records=self._idempotency_records,
            idempotency_candidates=self._idempotency_candidates,
            conversion_intent_candidates=self._conversion_intent_candidates,
            report_evidence_pack_candidates=self._report_evidence_pack_candidates,
        )

    def _record_for_idempotency_key(
        self, idempotency_key: str
    ) -> CandidatePersistenceRecord | None:
        candidate_id = self._idempotency_candidates.get(idempotency_key)
        if candidate_id is None:
            return None
        return self._candidate_records.get(candidate_id)

    def _transition_record(
        self,
        record: CandidatePersistenceRecord,
        *,
        target_status: IdeaLifecycleStatus,
        actor_subject: str,
        occurred_at_utc: datetime,
        attributes: Mapping[str, str],
    ) -> tuple[CandidatePersistenceRecord, AuditEvent]:
        candidate_id = record.candidate.candidate_id
        transitioned = transition_candidate(
            record.candidate,
            target_status,
            updated_at_utc=occurred_at_utc,
        )
        history_entry = LifecycleHistoryEntry(
            candidate_id=candidate_id,
            source_status=record.candidate.lifecycle_status,
            target_status=target_status,
            actor_subject=actor_subject,
            changed_at_utc=occurred_at_utc,
        )
        audit_attributes = {
            "source_status": record.candidate.lifecycle_status.value,
            "target_status": target_status.value,
            **dict(attributes),
        }
        audit_event = _audit_event(
            event_type="idea.lifecycle.transitioned",
            actor_subject=actor_subject,
            outcome="accepted",
            occurred_at_utc=occurred_at_utc,
            attributes=audit_attributes,
        )
        updated = replace(
            record,
            candidate=transitioned,
            lifecycle_history=(*record.lifecycle_history, history_entry),
            audit_events=(*record.audit_events, audit_event),
        )
        self._candidate_records[candidate_id] = updated
        return updated, audit_event


def evidence_hash_for_candidate(candidate: IdeaCandidate) -> str:
    return evidence_hash_for_source_refs(candidate.evidence_packet.source_refs)


def evidence_hash_for_source_refs(source_refs: tuple[SourceRef, ...]) -> str:
    payload = [
        {
            "content_hash": source_ref.content_hash,
            "data_quality_status": source_ref.data_quality_status,
            "freshness": source_ref.freshness.value,
            "product_id": source_ref.product_id,
            "product_version": source_ref.product_version,
            "source_system": source_ref.source_system.value,
        }
        for source_ref in sorted(source_refs, key=lambda ref: ref.product_id)
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _audit_event(
    *,
    event_type: str,
    actor_subject: str,
    outcome: str,
    occurred_at_utc: datetime,
    attributes: Mapping[str, str],
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        actor_subject=actor_subject,
        outcome=outcome,
        occurred_at_utc=occurred_at_utc,
        attributes=attributes,
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
