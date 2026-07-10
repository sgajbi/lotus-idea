from __future__ import annotations

from datetime import timedelta

from app.domain import (
    CandidatePersistenceRecord,
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    SourceSystem,
    create_downstream_submission_claim,
    finalize_downstream_submission,
)
from app.infrastructure.postgres_candidate_detail import load_candidate_record_by_id
from app.infrastructure.postgres_codecs import (
    conversion_intent_from_json,
    read_json_object,
    read_row_value,
    report_evidence_pack_from_json,
)
from app.infrastructure.postgres_protocols import PostgresConnection


def load_conversion_intent_by_id(
    connection: PostgresConnection,
    conversion_intent_id: str,
) -> GovernedConversionIntent | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-lookup-conversion-intent */
            SELECT conversion_intent_id, candidate_id, intent_json
            FROM idea_conversion_intent
            WHERE conversion_intent_id = %s
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
            SELECT candidate_id
            FROM idea_conversion_intent
            WHERE conversion_intent_id = %s
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
            SELECT report_evidence_pack_id, candidate_id, evidence_pack_json
            FROM idea_report_evidence_pack_request
            WHERE report_evidence_pack_id = %s
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
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-lookup-submission-idempotency */
            SELECT idempotency_key, request_fingerprint, resource_type, resource_id,
                   target, source_authority, status, downstream_failure_reason,
                   correlation_id, trace_id, submitted_at_utc
            FROM idea_downstream_submission
            WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return downstream_submission_from_row(rows[0])


def downstream_submission_from_row(row: object) -> DownstreamSubmissionRecord:
    submitted_at_utc = read_row_value(row, "submitted_at_utc")
    idempotency_key = read_row_value(row, "idempotency_key")
    lease_owner = "legacy-downstream-submission"
    lease_attempt_id = f"legacy-{idempotency_key}"
    claimed = create_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint=read_row_value(row, "request_fingerprint"),
        resource_type=DownstreamSubmissionResourceType(read_row_value(row, "resource_type")),
        resource_id=read_row_value(row, "resource_id"),
        target=ConversionTarget(read_row_value(row, "target")),
        source_authority=SourceSystem(read_row_value(row, "source_authority")),
        actor_subject=lease_owner,
        claimed_at_utc=submitted_at_utc,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=submitted_at_utc + timedelta(seconds=1),
        correlation_id=read_row_value(row, "correlation_id"),
        trace_id=read_row_value(row, "trace_id"),
    )
    finalized = finalize_downstream_submission(
        claimed,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        posture=DownstreamSubmissionPosture(read_row_value(row, "status")),
        finalized_at_utc=submitted_at_utc,
        failure_reason=read_row_value(row, "downstream_failure_reason"),
    )
    assert finalized.record is not None
    return finalized.record
