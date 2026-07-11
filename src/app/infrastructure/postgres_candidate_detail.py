from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.domain.audit import AuditEvent
from app.domain.ideas import IdeaLifecycleStatus
from app.domain.persistence import CandidatePersistenceRecord, LifecycleHistoryEntry
from app.infrastructure.postgres_codecs import (
    ai_explanation_lineage_from_json,
    conversion_intent_from_json,
    conversion_outcome_from_json,
    feedback_event_from_json,
    read_json_object,
    read_row_value,
    report_evidence_pack_from_json,
    review_decision_from_json,
)
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor
from app.infrastructure.postgres_review_queue import candidate_record_from_row


def load_candidate_record_by_id(
    connection: PostgresConnection,
    candidate_id: str,
) -> CandidatePersistenceRecord | None:
    with connection.cursor() as cursor:
        record = _load_base_candidate_record(cursor, candidate_id)
        if record is None:
            return None
        record = _attach_lifecycle_history(cursor, record)
        record = _attach_audit_events(cursor, record)
        record = _attach_review_decisions(cursor, record)
        record = _attach_feedback_events(cursor, record)
        record = _attach_conversion_intents(cursor, record)
        record = _attach_conversion_outcomes(cursor, record)
        record = _attach_report_evidence_packs(cursor, record)
        return _attach_ai_explanation_lineage_records(cursor, record)


def _load_base_candidate_record(
    cursor: PostgresCursor,
    candidate_id: str,
) -> CandidatePersistenceRecord | None:
    cursor.execute(
        """
        /* lotus-idea candidate-detail-base */
        SELECT candidate.candidate_id, candidate.evidence_hash,
               candidate.candidate_json, candidate.persisted_at_utc
        FROM idea_candidate_record candidate
        JOIN idea_data_lifecycle_control lifecycle
          ON lifecycle.candidate_id = candidate.candidate_id
        WHERE candidate.candidate_id = %s
          AND COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
        """,
        (candidate_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    return candidate_record_from_row(rows[0])


def _attach_lifecycle_history(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    candidate_id = record.candidate.candidate_id
    cursor.execute(
        """
        /* lotus-idea candidate-detail-lifecycle */
        SELECT candidate_id, source_status, target_status, actor_subject, changed_at_utc
        FROM idea_lifecycle_history
        WHERE candidate_id = %s
        ORDER BY changed_at_utc, lifecycle_history_id
        """,
        (candidate_id,),
    )
    return replace(
        record,
        lifecycle_history=tuple(
            LifecycleHistoryEntry(
                candidate_id=read_row_value(row, "candidate_id"),
                source_status=IdeaLifecycleStatus(read_row_value(row, "source_status")),
                target_status=IdeaLifecycleStatus(read_row_value(row, "target_status")),
                actor_subject=read_row_value(row, "actor_subject"),
                changed_at_utc=read_row_value(row, "changed_at_utc"),
            )
            for row in cursor.fetchall()
        ),
    )


def _attach_audit_events(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    candidate_id = record.candidate.candidate_id
    cursor.execute(
        """
        /* lotus-idea candidate-detail-audit */
        SELECT candidate_id, event_type, actor_subject, outcome, attributes_json, occurred_at_utc
        FROM idea_audit_event
        WHERE candidate_id = %s
        ORDER BY occurred_at_utc, audit_event_id
        """,
        (candidate_id,),
    )
    return replace(
        record,
        audit_events=tuple(
            AuditEvent(
                event_type=read_row_value(row, "event_type"),
                actor_subject=read_row_value(row, "actor_subject"),
                outcome=read_row_value(row, "outcome"),
                attributes=read_json_object(row, "attributes_json"),
                occurred_at_utc=read_row_value(row, "occurred_at_utc"),
            )
            for row in cursor.fetchall()
        ),
    )


def _attach_review_decisions(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    rows = _select_candidate_rows(
        cursor,
        table="idea_review_decision",
        columns="candidate_id, decision_json",
        candidate_id=record.candidate.candidate_id,
        order_by="decided_at_utc, review_decision_id",
        comment="candidate-detail-review-decisions",
    )
    return replace(
        record,
        review_decisions=tuple(
            review_decision_from_json(read_json_object(row, "decision_json")) for row in rows
        ),
    )


def _attach_feedback_events(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    rows = _select_candidate_rows(
        cursor,
        table="idea_feedback_event",
        columns="candidate_id, feedback_json",
        candidate_id=record.candidate.candidate_id,
        order_by="recorded_at_utc, feedback_event_id",
        comment="candidate-detail-feedback",
    )
    return replace(
        record,
        feedback_events=tuple(
            feedback_event_from_json(read_json_object(row, "feedback_json")) for row in rows
        ),
    )


def _attach_conversion_intents(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    rows = _select_candidate_rows(
        cursor,
        table="idea_conversion_intent",
        columns="conversion_intent_id, candidate_id, intent_json",
        candidate_id=record.candidate.candidate_id,
        order_by="requested_at_utc, conversion_intent_id",
        comment="candidate-detail-conversion-intents",
    )
    return replace(
        record,
        conversion_intents=tuple(
            conversion_intent_from_json(read_json_object(row, "intent_json")) for row in rows
        ),
    )


def _attach_conversion_outcomes(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    intent_ids = [intent.intent.conversion_intent_id for intent in record.conversion_intents]
    if not intent_ids:
        return record
    cursor.execute(
        """
        /* lotus-idea candidate-detail-conversion-outcomes */
        SELECT conversion_intent_id, outcome_json
        FROM idea_conversion_outcome
        WHERE conversion_intent_id = ANY(%s)
        ORDER BY recorded_at_utc, conversion_outcome_id
        """,
        (intent_ids,),
    )
    return replace(
        record,
        conversion_outcomes=tuple(
            conversion_outcome_from_json(read_json_object(row, "outcome_json"))
            for row in cursor.fetchall()
        ),
    )


def _attach_report_evidence_packs(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    rows = _select_candidate_rows(
        cursor,
        table="idea_report_evidence_pack_request",
        columns="report_evidence_pack_id, candidate_id, evidence_pack_json",
        candidate_id=record.candidate.candidate_id,
        order_by="requested_at_utc, report_evidence_pack_id",
        comment="candidate-detail-report-evidence-packs",
    )
    return replace(
        record,
        report_evidence_packs=tuple(
            report_evidence_pack_from_json(read_json_object(row, "evidence_pack_json"))
            for row in rows
        ),
    )


def _attach_ai_explanation_lineage_records(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> CandidatePersistenceRecord:
    rows = _select_candidate_rows(
        cursor,
        table="idea_ai_explanation_lineage",
        columns="ai_explanation_request_id, candidate_id, lineage_json",
        candidate_id=record.candidate.candidate_id,
        order_by="evaluated_at_utc, ai_explanation_request_id",
        comment="candidate-detail-ai-lineage",
    )
    return replace(
        record,
        ai_explanation_lineage_records=tuple(
            ai_explanation_lineage_from_json(read_json_object(row, "lineage_json")) for row in rows
        ),
    )


def _select_candidate_rows(
    cursor: PostgresCursor,
    *,
    table: str,
    columns: str,
    candidate_id: str,
    order_by: str,
    comment: str,
) -> tuple[Any, ...]:
    cursor.execute(
        f"""
        /* lotus-idea {comment} */
        SELECT {columns}
        FROM {table}
        WHERE candidate_id = %s
        ORDER BY {order_by}
        """,
        (candidate_id,),
    )
    return tuple(cursor.fetchall())
