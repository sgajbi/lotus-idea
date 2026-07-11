from __future__ import annotations

from app.domain import (
    CandidatePersistenceRecord,
    DownstreamSubmissionRecord,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
)
from app.infrastructure.postgres_candidate_detail import load_candidate_record_by_id
from app.infrastructure.postgres_codecs import (
    conversion_intent_from_json,
    read_json_object,
    read_row_value,
    report_evidence_pack_from_json,
)
from app.infrastructure.postgres_protocols import PostgresConnection
from app.infrastructure.postgres_downstream_submission import (
    load_postgres_downstream_submission_by_idempotency_key,
)


def load_conversion_intent_by_id(
    connection: PostgresConnection,
    conversion_intent_id: str,
) -> GovernedConversionIntent | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-lookup-conversion-intent */
            SELECT intent.conversion_intent_id, intent.candidate_id, intent.intent_json
            FROM idea_conversion_intent intent
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = intent.candidate_id
            WHERE intent.conversion_intent_id = %s
              AND COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            """,
            (conversion_intent_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return conversion_intent_from_json(read_json_object(rows[0], "intent_json"))


def load_candidate_record_for_conversion_intent(
    connection: PostgresConnection,
    conversion_intent_id: str,
) -> CandidatePersistenceRecord | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-lookup-conversion-candidate */
            SELECT intent.candidate_id
            FROM idea_conversion_intent intent
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = intent.candidate_id
            WHERE intent.conversion_intent_id = %s
              AND COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            """,
            (conversion_intent_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return load_candidate_record_by_id(connection, read_row_value(rows[0], "candidate_id"))


def load_report_evidence_pack_by_id(
    connection: PostgresConnection,
    report_evidence_pack_id: str,
) -> GovernedReportEvidencePack | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-lookup-report-evidence-pack */
            SELECT report.report_evidence_pack_id, report.candidate_id,
                   report.evidence_pack_json
            FROM idea_report_evidence_pack_request report
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = report.candidate_id
            WHERE report.report_evidence_pack_id = %s
              AND COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            """,
            (report_evidence_pack_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return report_evidence_pack_from_json(read_json_object(rows[0], "evidence_pack_json"))


def load_downstream_submission_by_idempotency_key(
    connection: PostgresConnection,
    idempotency_key: str,
) -> DownstreamSubmissionRecord | None:
    return load_postgres_downstream_submission_by_idempotency_key(connection, idempotency_key)
