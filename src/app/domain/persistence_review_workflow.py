from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping

from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord, evaluate_idempotency
from app.domain.outbox.events import EventLineageContext
from app.domain.persistence_models import (
    CandidatePersistenceRecord,
    LifecycleHistoryEntry,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
from app.domain.review_governance import (
    FeedbackResult,
    ReviewActionResult,
    ReviewMutationIdentity,
    feedback_mutation_identity_from_event,
    review_mutation_identity_from_decision,
)


class InMemoryReviewWorkflowRepositoryMixin:
    _candidate_records: dict[str, CandidatePersistenceRecord]
    _idempotency_records: dict[str, IdempotencyRecord]
    _idempotency_candidates: dict[str, str]
    _record_for_idempotency_key: Callable[[str], CandidatePersistenceRecord | None]
    _append_outbox_event: Callable[..., None]

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


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
