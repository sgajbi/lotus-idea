from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Mapping

from app.domain.audit import AuditEvent
from app.domain.outbox.events import (
    EventLineageContext,
    OutboxEventRecord,
)
from app.domain.evidence_hashing import evidence_hash_for_candidate, evidence_hash_for_source_refs
from app.domain.downstream_submission import DownstreamSubmissionRecord
from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord, evaluate_idempotency
from app.domain.persistence_lookups import InMemoryIdeaLookupMixin
from app.domain.persistence_ai_lineage import InMemoryAIExplanationRepositoryMixin
from app.domain.outbox.persistence import InMemoryOutboxRepositoryMixin
from app.domain.outbox.recovery import OutboxRecoveryAuditRecord
from app.domain.persistence_downstream_submission import (
    InMemoryDownstreamSubmissionRepositoryMixin,
)
from app.domain.persistence_conversion_outcomes import (
    conversion_outcome_identity_result,
    precheck_conversion_outcome_identity_mutation,
)
from app.domain.persistence_models import (
    CandidatePersistenceDecision,
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    EvidenceReplayResult,
    EvidenceReplayStatus,
    IdeaRepositorySnapshot,
    LifecycleHistoryEntry,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
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
)
from app.domain.conversion_outcome_policy import (
    ConversionOutcomeIdentity,
    ConversionOutcomePolicyViolation,
    validate_conversion_outcome_progression,
)
from app.domain.report_evidence import ReportEvidencePackResult
from app.domain.lotus_ai_attestation_replay import LotusAIAttestationReplayIndex
from app.domain.ai_provider_retention_replay import AIProviderRetentionReplayIndex
from app.domain.review_governance import (
    FeedbackResult,
    ReviewActionResult,
    ReviewMutationIdentity,
    feedback_mutation_identity_from_event,
    review_mutation_identity_from_decision,
)


class InMemoryIdeaRepository(
    InMemoryIdeaLookupMixin,
    InMemoryAIExplanationRepositoryMixin,
    InMemoryOutboxRepositoryMixin,
    InMemoryDownstreamSubmissionRepositoryMixin,
):
    """Behavioral reference repository for local development and unit tests."""

    def __init__(self, snapshot: IdeaRepositorySnapshot | None = None) -> None:
        self._candidate_records: dict[str, CandidatePersistenceRecord] = {}
        self._idempotency_records: dict[str, IdempotencyRecord] = {}
        self._idempotency_candidates: dict[str, str] = {}
        self._conversion_intent_candidates: dict[str, str] = {}
        self._report_evidence_pack_candidates: dict[str, str] = {}
        self._ai_explanation_lineage_candidates: dict[str, str] = {}
        self._lotus_ai_attestation_replay = LotusAIAttestationReplayIndex()
        self._ai_provider_retention_replay = AIProviderRetentionReplayIndex()
        self._outbox_events: dict[str, OutboxEventRecord] = {}
        self._outbox_recovery_records: dict[str, OutboxRecoveryAuditRecord] = {}
        self._downstream_submission_records: dict[str, DownstreamSubmissionRecord] = {}
        if snapshot is not None:
            self._candidate_records.update(snapshot.candidate_records)
            self._idempotency_records.update(snapshot.idempotency_records)
            self._idempotency_candidates.update(snapshot.idempotency_candidates)
            self._conversion_intent_candidates.update(snapshot.conversion_intent_candidates)
            self._report_evidence_pack_candidates.update(snapshot.report_evidence_pack_candidates)
            self._ai_explanation_lineage_candidates.update(
                snapshot.ai_explanation_lineage_candidates
            )
            self._outbox_events.update(snapshot.outbox_events)
            self._downstream_submission_records.update(snapshot.downstream_submission_records)
            self._lotus_ai_attestation_replay.restore(
                (lineage.request_id, lineage.attestation_receipt)
                for record in self._candidate_records.values()
                for lineage in getattr(record, "ai_explanation_lineage_records", ())
                if lineage.attestation_receipt is not None
            )
            self._ai_provider_retention_replay.restore(
                (lineage.request_id, lineage.provider_retention_receipt)
                for record in self._candidate_records.values()
                for lineage in getattr(record, "ai_explanation_lineage_records", ())
                if lineage.provider_retention_receipt is not None
            )

    def persist_candidate(
        self,
        candidate: IdeaCandidate,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
        event_lineage: EventLineageContext | None = None,
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
        self._append_outbox_event(
            event_type="idea.candidate.persisted.v1",
            aggregate_id=candidate.candidate_id,
            occurred_at_utc=event_time,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "candidate_family": candidate.family.value,
                "lifecycle_status": candidate.lifecycle_status.value,
                "review_posture": candidate.review_posture.value,
            },
        )
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
        event_lineage: EventLineageContext | None = None,
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
        self._append_outbox_event(
            event_type="idea.lifecycle.transitioned.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=event_time,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "source_status": record.candidate.lifecycle_status.value,
                "target_status": target_status.value,
            },
        )
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

    def record_outbox_delivery_run_request(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> IdempotencyDecision:
        _require_text(idempotency_key, "idempotency_key")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.ACCEPTED:
            self._idempotency_records[idempotency_key] = idempotency_record
        return idempotency_decision

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
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

        identity_result = self._review_identity_result(
            identity=review_mutation_identity_from_decision(result.decision),
            idempotency_key=idempotency_key,
            idempotency_record=idempotency_record,
        )
        if identity_result is not None:
            return identity_result

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
        self._append_outbox_event(
            event_type="idea.review.decision_recorded.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=result.decision.decided_at_utc,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "action": result.decision.action.value,
                "resulting_posture": result.decision.resulting_posture.value,
            },
        )
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
        identity: ReviewMutationIdentity,
    ) -> ReviewPersistenceResult | None:
        _require_text(idempotency_key, "idempotency_key")
        existing_idempotency = self._idempotency_records.get(idempotency_key)
        idempotency_decision, idempotency_record = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        if idempotency_decision is IdempotencyDecision.ACCEPTED:
            return self._review_identity_result(
                identity=identity,
                idempotency_key=idempotency_key,
                idempotency_record=idempotency_record,
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
        event_lineage: EventLineageContext | None = None,
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

        identity_result = self._review_identity_result(
            identity=feedback_mutation_identity_from_event(result.feedback_event),
            idempotency_key=idempotency_key,
            idempotency_record=idempotency_record,
        )
        if identity_result is not None:
            return identity_result

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
        self._append_outbox_event(
            event_type="idea.feedback.recorded.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=result.feedback_event.feedback.recorded_at_utc,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "feedback_outcome": result.feedback_event.feedback.outcome.value,
                "actor_role": result.feedback_event.actor_role.value,
            },
        )
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
        event_lineage: EventLineageContext | None = None,
    ) -> ConversionPersistenceResult:
        _require_text(idempotency_key, "idempotency_key")
        _require_matching_conversion_intent_idempotency(result, idempotency_key)
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
        self._append_outbox_event(
            event_type="idea.conversion.intent_requested.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=result.conversion_intent.intent.requested_at_utc,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "target": result.conversion_intent.intent.target.value,
                "target_source_authority": result.conversion_intent.target_source_authority.value,
            },
        )
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def record_conversion_outcome(
        self,
        result: ConversionOutcomeResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
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

        identity_result = conversion_outcome_identity_result(
            candidate_records=self._candidate_records,
            idempotency_records=self._idempotency_records,
            idempotency_candidates=self._idempotency_candidates,
            identity=result.conversion_outcome.identity,
            idempotency_key=idempotency_key,
            idempotency_record=idempotency_record,
        )
        if identity_result is not None:
            return identity_result

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
        try:
            validate_conversion_outcome_progression(
                tuple(
                    outcome.identity
                    for outcome in record.conversion_outcomes
                    if outcome.conversion_intent_id == conversion_intent_id
                ),
                result.conversion_outcome.identity,
            )
        except ConversionOutcomePolicyViolation:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.OUTCOME_CONFLICT,
                record=record,
            )

        updated = replace(
            record,
            audit_events=(*record.audit_events, result.audit_event),
            conversion_outcomes=(*record.conversion_outcomes, result.conversion_outcome),
        )
        self._candidate_records[candidate_id] = updated
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = candidate_id
        self._append_outbox_event(
            event_type="idea.conversion.outcome_recorded.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=result.conversion_outcome.outcome.recorded_at_utc,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "source_system": result.conversion_outcome.source_system.value,
                "source_event_version": str(result.conversion_outcome.source_event_version),
                "status": result.conversion_outcome.outcome.status.value,
                "supersedes_outcome": str(
                    result.conversion_outcome.supersedes_conversion_outcome_id is not None
                ).lower(),
                "target": result.conversion_outcome.target.value,
            },
        )
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.ACCEPTED,
            record=updated,
            audit_event=result.audit_event,
        )

    def precheck_conversion_outcome_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        identity: ConversionOutcomeIdentity,
    ) -> ConversionPersistenceResult | None:
        _require_text(idempotency_key, "idempotency_key")
        return precheck_conversion_outcome_identity_mutation(
            candidate_records=self._candidate_records,
            idempotency_records=self._idempotency_records,
            idempotency_candidates=self._idempotency_candidates,
            idempotency_key=idempotency_key,
            payload=payload,
            identity=identity,
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

    def record_report_evidence_pack(
        self,
        result: ReportEvidencePackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
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
        self._append_outbox_event(
            event_type="idea.report_evidence_pack.requested.v1",
            aggregate_id=candidate_id,
            occurred_at_utc=result.evidence_pack.requested_at_utc,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage,
            payload={
                "purpose": result.evidence_pack.purpose.value,
                "report_source_authority": result.evidence_pack.report_source_authority.value,
                "render_source_authority": result.evidence_pack.render_source_authority.value,
                "archive_source_authority": result.evidence_pack.archive_source_authority.value,
            },
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
            ai_explanation_lineage_candidates=self._ai_explanation_lineage_candidates,
            outbox_events=self._outbox_events,
            downstream_submission_records=self._downstream_submission_records,
        )

    def _record_for_idempotency_key(
        self, idempotency_key: str
    ) -> CandidatePersistenceRecord | None:
        candidate_id = self._idempotency_candidates.get(idempotency_key)
        if candidate_id is None:
            return None
        return self._candidate_records.get(candidate_id)

    def _review_identity_result(
        self,
        *,
        identity: ReviewMutationIdentity,
        idempotency_key: str,
        idempotency_record: IdempotencyRecord,
    ) -> ReviewPersistenceResult | None:
        existing = self._review_identity_record(identity)
        if existing is None:
            return None
        existing_identity, record = existing
        if existing_identity != identity:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.IDENTITY_CONFLICT,
                record=record,
            )
        self._idempotency_records[idempotency_key] = idempotency_record
        self._idempotency_candidates[idempotency_key] = record.candidate.candidate_id
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.REPLAYED,
            record=record,
        )

    def _review_identity_record(
        self,
        identity: ReviewMutationIdentity,
    ) -> tuple[ReviewMutationIdentity, CandidatePersistenceRecord] | None:
        for record in self._candidate_records.values():
            for decision in record.review_decisions:
                existing = review_mutation_identity_from_decision(decision)
                if existing.mutation_type is identity.mutation_type and (
                    existing.resource_id == identity.resource_id
                ):
                    return existing, record
            for feedback in record.feedback_events:
                existing = feedback_mutation_identity_from_event(feedback)
                if existing.mutation_type is identity.mutation_type and (
                    existing.resource_id == identity.resource_id
                ):
                    return existing, record
        return None

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


def _require_matching_conversion_intent_idempotency(
    result: ConversionIntentResult,
    idempotency_key: str,
) -> None:
    if result.conversion_intent.idempotency_key != idempotency_key:
        raise ValueError("conversion intent idempotency key must match repository idempotency key")


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")


__all__ = [
    "CandidatePersistenceDecision",
    "CandidatePersistenceRecord",
    "CandidatePersistenceResult",
    "ConversionPersistenceDecision",
    "ConversionPersistenceResult",
    "EvidencePackPersistenceDecision",
    "EvidencePackPersistenceResult",
    "EvidenceReplayResult",
    "EvidenceReplayStatus",
    "IdeaRepositorySnapshot",
    "InMemoryIdeaRepository",
    "LifecycleHistoryEntry",
    "LifecyclePersistenceDecision",
    "LifecyclePersistenceResult",
    "ReviewPersistenceDecision",
    "ReviewPersistenceResult",
]
