from __future__ import annotations

from typing import Any, Protocol

from app.domain import (
    CandidatePersistenceRecord,
    DownstreamSubmissionRecord,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    GovernedFeedbackEvent,
    GovernedReportEvidencePack,
    GovernedReviewDecision,
    IdeaRepositorySnapshot,
    LifecycleHistoryEntry,
    OutboxEventRecord,
)
from app.domain.audit import AuditEvent
from app.domain.idempotency import IdempotencyRecord
from app.infrastructure.postgres_ai_lineage_writes import insert_ai_explanation_lineage_record


class PostgresSnapshotDeltaWriter(Protocol):
    def _insert_candidate_record(
        self,
        cursor: Any,
        record: CandidatePersistenceRecord,
    ) -> None: ...

    def _insert_record_details(
        self,
        cursor: Any,
        record: CandidatePersistenceRecord,
    ) -> None: ...

    def _update_candidate_record(
        self,
        cursor: Any,
        before: CandidatePersistenceRecord,
        record: CandidatePersistenceRecord,
    ) -> None: ...

    def _insert_idempotency_record(
        self,
        cursor: Any,
        record: IdempotencyRecord,
        *,
        candidate_id: str | None,
        snapshot: IdeaRepositorySnapshot,
    ) -> None: ...

    def _insert_outbox_event(
        self,
        cursor: Any,
        event: OutboxEventRecord,
    ) -> None: ...

    def _insert_downstream_submission_record(
        self,
        cursor: Any,
        record: DownstreamSubmissionRecord,
    ) -> None: ...

    def _insert_lifecycle_history_entry(
        self,
        cursor: Any,
        candidate_id: str,
        entry: LifecycleHistoryEntry,
        index: int,
    ) -> None: ...

    def _insert_audit_event(
        self,
        cursor: Any,
        candidate_id: str,
        event: AuditEvent,
        index: int,
    ) -> None: ...

    def _insert_review_decision(
        self,
        cursor: Any,
        candidate_id: str,
        decision: GovernedReviewDecision,
    ) -> None: ...

    def _insert_feedback_event(
        self,
        cursor: Any,
        candidate_id: str,
        feedback: GovernedFeedbackEvent,
    ) -> None: ...

    def _insert_conversion_intent(
        self,
        cursor: Any,
        candidate_id: str,
        intent: GovernedConversionIntent,
    ) -> None: ...

    def _insert_conversion_outcome(
        self,
        cursor: Any,
        outcome: GovernedConversionOutcome,
    ) -> None: ...

    def _insert_report_evidence_pack(
        self,
        cursor: Any,
        candidate_id: str,
        evidence_pack: GovernedReportEvidencePack,
    ) -> None: ...


def apply_postgres_snapshot_delta(
    writer: PostgresSnapshotDeltaWriter,
    cursor: Any,
    *,
    before: IdeaRepositorySnapshot,
    after: IdeaRepositorySnapshot,
) -> None:
    for candidate_id, after_record in after.candidate_records.items():
        if candidate_id not in before.candidate_records:
            writer._insert_candidate_record(cursor, after_record)

    for key, idempotency_record in after.idempotency_records.items():
        if key not in before.idempotency_records:
            writer._insert_idempotency_record(
                cursor,
                idempotency_record,
                candidate_id=after.idempotency_candidates.get(key),
                snapshot=after,
            )

    for candidate_id, after_record in after.candidate_records.items():
        before_record = before.candidate_records.get(candidate_id)
        if before_record is None:
            writer._insert_record_details(cursor, after_record)
            continue

        _insert_review_identity_delta(writer, cursor, before_record, after_record)
        _insert_conversion_outcome_delta(writer, cursor, before_record, after_record)
        if after_record.candidate != before_record.candidate:
            writer._update_candidate_record(cursor, before_record, after_record)
        _insert_record_detail_delta(writer, cursor, before_record, after_record)

    for event_id, outbox_event in after.outbox_events.items():
        if event_id not in before.outbox_events:
            writer._insert_outbox_event(cursor, outbox_event)

    for key, submission_record in after.downstream_submission_records.items():
        if key not in before.downstream_submission_records:
            writer._insert_downstream_submission_record(cursor, submission_record)


def _insert_record_detail_delta(
    writer: PostgresSnapshotDeltaWriter,
    cursor: Any,
    before: CandidatePersistenceRecord,
    after: CandidatePersistenceRecord,
) -> None:
    candidate_id = after.candidate.candidate_id
    for offset, entry in enumerate(
        after.lifecycle_history[len(before.lifecycle_history) :],
        start=len(before.lifecycle_history) + 1,
    ):
        writer._insert_lifecycle_history_entry(cursor, candidate_id, entry, offset)
    for offset, event in enumerate(
        after.audit_events[len(before.audit_events) :],
        start=len(before.audit_events) + 1,
    ):
        writer._insert_audit_event(cursor, candidate_id, event, offset)

    conversion_intent_ids = {
        intent.intent.conversion_intent_id for intent in before.conversion_intents
    }
    for intent in after.conversion_intents:
        if intent.intent.conversion_intent_id not in conversion_intent_ids:
            writer._insert_conversion_intent(cursor, candidate_id, intent)

    report_pack_ids = {pack.report_evidence_pack_id for pack in before.report_evidence_packs}
    for evidence_pack in after.report_evidence_packs:
        if evidence_pack.report_evidence_pack_id not in report_pack_ids:
            writer._insert_report_evidence_pack(cursor, candidate_id, evidence_pack)

    lineage_request_ids = {lineage.request_id for lineage in before.ai_explanation_lineage_records}
    for lineage_record in after.ai_explanation_lineage_records:
        if lineage_record.request_id not in lineage_request_ids:
            insert_ai_explanation_lineage_record(
                cursor,
                candidate_id,
                lineage_record,
            )


def _insert_review_identity_delta(
    writer: PostgresSnapshotDeltaWriter,
    cursor: Any,
    before: CandidatePersistenceRecord,
    after: CandidatePersistenceRecord,
) -> None:
    candidate_id = after.candidate.candidate_id
    review_ids = {decision.review_id for decision in before.review_decisions}
    for decision in after.review_decisions:
        if decision.review_id not in review_ids:
            writer._insert_review_decision(cursor, candidate_id, decision)

    feedback_ids = {event.feedback.feedback_id for event in before.feedback_events}
    for feedback in after.feedback_events:
        if feedback.feedback.feedback_id not in feedback_ids:
            writer._insert_feedback_event(cursor, candidate_id, feedback)


def _insert_conversion_outcome_delta(
    writer: PostgresSnapshotDeltaWriter,
    cursor: Any,
    before: CandidatePersistenceRecord,
    after: CandidatePersistenceRecord,
) -> None:
    conversion_outcome_ids = {
        outcome.outcome.conversion_outcome_id for outcome in before.conversion_outcomes
    }
    for outcome in after.conversion_outcomes:
        if outcome.outcome.conversion_outcome_id not in conversion_outcome_ids:
            writer._insert_conversion_outcome(cursor, outcome)
