from __future__ import annotations

import hashlib
from typing import Any

from psycopg.types.json import Jsonb


def redact_candidate_graph(
    cursor: Any,
    *,
    candidate_id: str,
    tenant_id: str,
    tombstone_sha256: str,
) -> dict[str, int]:
    actor_tombstone = _actor_tombstone(candidate_id, tenant_id)
    payload = Jsonb(
        {
            "data_lifecycle_state": "erased",
            "tombstone_sha256": tombstone_sha256,
        }
    )
    statements = (
        *_advisory_redaction_statements(candidate_id, actor_tombstone, payload),
        *_delivery_redaction_statements(candidate_id, actor_tombstone, payload),
    )
    counts: dict[str, int] = {}
    for table, query, params in statements:
        _execute_count(cursor, counts, table, query, params)
    return counts


def _advisory_redaction_statements(
    candidate_id: str,
    actor_tombstone: str,
    payload: Jsonb,
) -> tuple[tuple[str, str, tuple[Any, ...]], ...]:
    return (
        (
            "idea_candidate_record",
            "UPDATE idea_candidate_record SET candidate_json = %s WHERE candidate_id = %s",
            (payload, candidate_id),
        ),
        (
            "idea_candidate_state_quarantine",
            "UPDATE idea_candidate_state_quarantine SET candidate_json = %s WHERE candidate_id = %s",
            (payload, candidate_id),
        ),
        (
            "idea_lifecycle_history",
            "UPDATE idea_lifecycle_history SET actor_subject = %s WHERE candidate_id = %s",
            (actor_tombstone, candidate_id),
        ),
        (
            "idea_audit_event",
            """UPDATE idea_audit_event SET actor_subject = %s, attributes_json = %s
               WHERE candidate_id = %s""",
            (actor_tombstone, payload, candidate_id),
        ),
        (
            "idea_review_decision",
            """UPDATE idea_review_decision SET actor_subject = %s, decision_json = %s
               WHERE candidate_id = %s""",
            (actor_tombstone, payload, candidate_id),
        ),
        (
            "idea_feedback_event",
            """UPDATE idea_feedback_event SET actor_subject = %s, feedback_json = %s
               WHERE candidate_id = %s""",
            (actor_tombstone, payload, candidate_id),
        ),
        (
            "idea_conversion_intent",
            """UPDATE idea_conversion_intent SET actor_subject = %s, intent_json = %s
               WHERE candidate_id = %s""",
            (actor_tombstone, payload, candidate_id),
        ),
        (
            "idea_conversion_outcome",
            """UPDATE idea_conversion_outcome outcome
               SET actor_subject = %s, outcome_json = %s
               FROM idea_conversion_intent intent
               WHERE intent.conversion_intent_id = outcome.conversion_intent_id
                 AND intent.candidate_id = %s""",
            (actor_tombstone, payload, candidate_id),
        ),
        (
            "idea_conversion_outcome_quarantine",
            """UPDATE idea_conversion_outcome_quarantine quarantine SET outcome_json = %s
               FROM idea_conversion_intent intent
               WHERE intent.conversion_intent_id = quarantine.conversion_intent_id
                 AND intent.candidate_id = %s""",
            (payload, candidate_id),
        ),
        (
            "idea_report_evidence_pack_request",
            """UPDATE idea_report_evidence_pack_request SET evidence_pack_json = %s
               WHERE candidate_id = %s""",
            (payload, candidate_id),
        ),
        (
            "idea_ai_explanation_lineage",
            "UPDATE idea_ai_explanation_lineage SET lineage_json = %s WHERE candidate_id = %s",
            (payload, candidate_id),
        ),
    )


def _delivery_redaction_statements(
    candidate_id: str,
    actor_tombstone: str,
    payload: Jsonb,
) -> tuple[tuple[str, str, tuple[Any, ...]], ...]:
    return (
        (
            "idea_outbox_event",
            """UPDATE idea_outbox_event SET payload_json = %s,
                   failure_reason = CASE WHEN failure_reason IS NULL THEN NULL
                                         ELSE 'redacted_by_data_lifecycle' END
               WHERE aggregate_type = 'idea_candidate' AND aggregate_id = %s""",
            (payload, candidate_id),
        ),
        (
            "idea_outbox_recovery_audit",
            """UPDATE idea_outbox_recovery_audit recovery SET actor_subject = %s,
                   original_failure_reason = 'redacted_by_data_lifecycle',
                   recovery_reason = 'redacted_by_data_lifecycle'
               FROM idea_outbox_event event
               WHERE event.outbox_event_id = recovery.outbox_event_id
                 AND event.aggregate_type = 'idea_candidate' AND event.aggregate_id = %s""",
            (actor_tombstone, candidate_id),
        ),
        (
            "idea_downstream_submission",
            """UPDATE idea_downstream_submission submission SET audit_json = %s,
                   downstream_failure_reason = CASE
                       WHEN downstream_failure_reason IS NULL THEN NULL
                       ELSE 'redacted_by_data_lifecycle' END,
                   correlation_id = NULL, trace_id = NULL
               WHERE (submission.resource_type = 'conversion_intent'
                      AND submission.resource_id IN (
                          SELECT conversion_intent_id FROM idea_conversion_intent
                          WHERE candidate_id = %s))
                  OR (submission.resource_type = 'report_evidence_pack'
                      AND submission.resource_id IN (
                          SELECT report_evidence_pack_id
                          FROM idea_report_evidence_pack_request WHERE candidate_id = %s))""",
            (payload, candidate_id, candidate_id),
        ),
    )


def purge_expired_candidate_payloads(cursor: Any, *, candidate_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    _execute_count(
        cursor,
        counts,
        "idea_candidate_state_quarantine",
        "DELETE FROM idea_candidate_state_quarantine WHERE candidate_id = %s",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_conversion_outcome_quarantine",
        """DELETE FROM idea_conversion_outcome_quarantine quarantine
           USING idea_conversion_intent intent
           WHERE intent.conversion_intent_id = quarantine.conversion_intent_id
             AND intent.candidate_id = %s""",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_ai_explanation_lineage",
        "DELETE FROM idea_ai_explanation_lineage WHERE candidate_id = %s",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_feedback_event",
        "DELETE FROM idea_feedback_event WHERE candidate_id = %s",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_downstream_submission",
        """DELETE FROM idea_downstream_submission submission
           WHERE (
               submission.resource_type = 'conversion_intent'
               AND submission.resource_id IN (
                   SELECT conversion_intent_id FROM idea_conversion_intent
                   WHERE candidate_id = %s
               )
           ) OR (
               submission.resource_type = 'report_evidence_pack'
               AND submission.resource_id IN (
                   SELECT report_evidence_pack_id FROM idea_report_evidence_pack_request
                   WHERE candidate_id = %s
               )
           )""",
        (candidate_id, candidate_id),
    )
    _execute_count(
        cursor,
        counts,
        "idea_outbox_recovery_audit",
        """DELETE FROM idea_outbox_recovery_audit recovery
           USING idea_outbox_event event
           WHERE event.outbox_event_id = recovery.outbox_event_id
             AND event.aggregate_type = 'idea_candidate'
             AND event.aggregate_id = %s""",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_outbox_event",
        """DELETE FROM idea_outbox_event
           WHERE aggregate_type = 'idea_candidate' AND aggregate_id = %s""",
        (candidate_id,),
    )
    _execute_count(
        cursor,
        counts,
        "idea_idempotency_record",
        "DELETE FROM idea_idempotency_record WHERE candidate_id = %s",
        (candidate_id,),
    )
    return counts


def _execute_count(
    cursor: Any,
    counts: dict[str, int],
    table: str,
    query: str,
    params: tuple[Any, ...],
) -> None:
    cursor.execute(query, params)
    counts[table] = counts.get(table, 0) + max(int(getattr(cursor, "rowcount", 0)), 0)


def _actor_tombstone(candidate_id: str, tenant_id: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}:{candidate_id}:actor".encode("utf-8")).hexdigest()
    return f"redacted-{digest[:24]}"
