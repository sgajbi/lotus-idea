from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from psycopg.types.json import Jsonb

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionAuditAction,
    DownstreamSubmissionAuditEntry,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionClaimResult,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionMutationResult,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    ReportMaterializationReceiptEvidence,
    SourceSystem,
    evaluate_downstream_submission_claim,
    finalize_downstream_submission,
    reconcile_downstream_submission,
)
from app.infrastructure.postgres_codecs import decode_datetime, read_row_value
from app.infrastructure.data_lifecycle.postgres_policy import DataLifecycleWriteBlockedError
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor


DOWNSTREAM_SUBMISSION_COLUMNS = """
idempotency_key, request_fingerprint, resource_type, resource_id, target,
source_authority, status, downstream_failure_reason, correlation_id, trace_id,
submitted_at_utc, support_reference, attempt_count, updated_at_utc, lease_owner,
lease_attempt_id, lease_expires_at_utc, audit_json, owner_receipt_json
"""
RECONCILIATION_POSTURES = (
    DownstreamSubmissionPosture.IN_FLIGHT.value,
    DownstreamSubmissionPosture.RECONCILIATION_REQUIRED.value,
)


def claim_postgres_downstream_submission(
    connection: PostgresConnection,
    record: DownstreamSubmissionRecord,
) -> DownstreamSubmissionClaimResult:
    try:
        with connection.cursor() as cursor:
            _lock_active_resource_lifecycle(cursor, record)
            cursor.execute(
                f"""
                /* lotus-idea downstream-submission-claim */
                INSERT INTO idea_downstream_submission (
                    {DOWNSTREAM_SUBMISSION_COLUMNS}
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                RETURNING {DOWNSTREAM_SUBMISSION_COLUMNS}
                """,
                downstream_submission_values(record),
            )
            inserted = cursor.fetchall()
            if inserted:
                connection.commit()
                return DownstreamSubmissionClaimResult(
                    decision=DownstreamSubmissionClaimDecision.ACCEPTED,
                    record=downstream_submission_from_row(inserted[0]),
                )
            existing = _load_by_idempotency_key(cursor, record.idempotency_key, for_update=True)
            if existing is None:
                support_collision = _load_by_support_reference(
                    cursor,
                    record.support_reference,
                    for_update=True,
                )
                if support_collision is not None:
                    raise RuntimeError("downstream submission support reference collision")
                raise RuntimeError("downstream submission claim conflict was not recoverable")
            decision = evaluate_downstream_submission_claim(
                existing,
                request_fingerprint=record.request_fingerprint,
            )
        connection.commit()
        return DownstreamSubmissionClaimResult(decision=decision, record=existing)
    except Exception:
        connection.rollback()
        raise


def _lock_active_resource_lifecycle(
    cursor: PostgresCursor,
    record: DownstreamSubmissionRecord,
) -> None:
    resource_contract = {
        DownstreamSubmissionResourceType.CONVERSION_INTENT: (
            "idea_conversion_intent",
            "conversion_intent_id",
        ),
        DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK: (
            "idea_report_evidence_pack_request",
            "report_evidence_pack_id",
        ),
    }
    table_name, identity_column = resource_contract[record.resource_type]
    cursor.execute(
        f"""
        /* lotus-idea downstream-submission-lifecycle-fence */
        SELECT lifecycle.candidate_id, lifecycle.state, lifecycle.held_from_state
        FROM {table_name} resource
        JOIN idea_data_lifecycle_control lifecycle
          ON lifecycle.candidate_id = resource.candidate_id
        WHERE resource.{identity_column} = %s
        FOR UPDATE OF lifecycle
        """,
        (record.resource_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        raise DataLifecycleWriteBlockedError(record.resource_id, "resource_missing_or_erased")
    state = read_row_value(rows[0], "held_from_state") or read_row_value(rows[0], "state")
    if state != "active":
        raise DataLifecycleWriteBlockedError(record.resource_id, "candidate_erased")


def finalize_postgres_downstream_submission(
    connection: PostgresConnection,
    *,
    idempotency_key: str,
    lease_owner: str,
    lease_attempt_id: str,
    posture: DownstreamSubmissionPosture,
    finalized_at_utc: datetime,
    failure_reason: str | None = None,
    owner_receipt: DownstreamSubmissionOwnerReceipt | None = None,
) -> DownstreamSubmissionMutationResult:
    try:
        with connection.cursor() as cursor:
            existing = _load_by_idempotency_key(cursor, idempotency_key, for_update=True)
            if existing is None:
                connection.commit()
                return DownstreamSubmissionMutationResult(
                    decision=DownstreamSubmissionMutationDecision.NOT_FOUND,
                    record=None,
                    blocker="downstream_submission_not_found",
                )
            result = finalize_downstream_submission(
                existing,
                lease_owner=lease_owner,
                lease_attempt_id=lease_attempt_id,
                posture=posture,
                finalized_at_utc=finalized_at_utc,
                failure_reason=failure_reason,
                owner_receipt=owner_receipt,
            )
            if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
                assert result.record is not None
                _update_mutable_submission_state(cursor, result.record)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise


def load_postgres_downstream_submission_by_idempotency_key(
    connection: PostgresConnection,
    idempotency_key: str,
) -> DownstreamSubmissionRecord | None:
    with connection.cursor() as cursor:
        return _load_by_idempotency_key(cursor, idempotency_key, for_update=False)


def load_postgres_downstream_submission_by_support_reference(
    connection: PostgresConnection,
    support_reference: str,
) -> DownstreamSubmissionRecord | None:
    with connection.cursor() as cursor:
        return _load_by_support_reference(cursor, support_reference, for_update=False)


def load_postgres_downstream_submissions_for_candidate(
    connection: PostgresConnection,
    candidate_id: str,
) -> tuple[DownstreamSubmissionRecord, ...]:
    if not candidate_id.strip():
        raise ValueError("candidate_id is required")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            /* lotus-idea candidate-detail-downstream-submissions */
            SELECT {DOWNSTREAM_SUBMISSION_COLUMNS}
            FROM idea_downstream_submission
            WHERE (resource_type, resource_id) IN (
                SELECT 'conversion_intent', conversion_intent_id
                FROM idea_conversion_intent
                WHERE candidate_id = %s
                UNION ALL
                SELECT 'report_evidence_pack', report_evidence_pack_id
                FROM idea_report_evidence_pack_request
                WHERE candidate_id = %s
            )
            ORDER BY submitted_at_utc, resource_type, resource_id, target, updated_at_utc
            """,
            (candidate_id, candidate_id),
        )
        return tuple(downstream_submission_from_row(row) for row in cursor.fetchall())


def load_postgres_downstream_submissions_requiring_reconciliation(
    connection: PostgresConnection,
    *,
    limit: int,
) -> tuple[DownstreamSubmissionRecord, ...]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            /* lotus-idea downstream-submission-reconciliation-list */
            SELECT {DOWNSTREAM_SUBMISSION_COLUMNS}
            FROM idea_downstream_submission
            WHERE status IN (%s, %s)
            ORDER BY updated_at_utc, support_reference
            LIMIT %s
            """,
            (*RECONCILIATION_POSTURES, limit),
        )
        return tuple(downstream_submission_from_row(row) for row in cursor.fetchall())


def reconcile_postgres_downstream_submission(
    connection: PostgresConnection,
    *,
    support_reference: str,
    resolution: DownstreamSubmissionResolution,
    actor_subject: str,
    reason: str,
    change_reference: str,
    reconciled_at_utc: datetime,
) -> DownstreamSubmissionMutationResult:
    try:
        with connection.cursor() as cursor:
            existing = _load_by_support_reference(cursor, support_reference, for_update=True)
            if existing is None:
                connection.commit()
                return DownstreamSubmissionMutationResult(
                    decision=DownstreamSubmissionMutationDecision.NOT_FOUND,
                    record=None,
                    blocker="downstream_submission_not_found",
                )
            result = reconcile_downstream_submission(
                existing,
                resolution=resolution,
                actor_subject=actor_subject,
                reason=reason,
                change_reference=change_reference,
                reconciled_at_utc=reconciled_at_utc,
            )
            if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
                assert result.record is not None
                _update_mutable_submission_state(cursor, result.record)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise


def downstream_submission_values(record: DownstreamSubmissionRecord) -> tuple[Any, ...]:
    return (
        record.idempotency_key,
        record.request_fingerprint,
        record.resource_type.value,
        record.resource_id,
        record.target.value,
        record.source_authority.value,
        record.status.value,
        record.downstream_failure_reason,
        record.correlation_id,
        record.trace_id,
        record.submitted_at_utc,
        record.support_reference,
        record.attempt_count,
        record.updated_at_utc,
        record.lease_owner,
        record.lease_attempt_id,
        record.lease_expires_at_utc,
        Jsonb([downstream_submission_audit_to_json(entry) for entry in record.audit_history]),
        Jsonb(_owner_receipt_to_json(record.owner_receipt)) if record.owner_receipt else None,
    )


def downstream_submission_from_row(row: object) -> DownstreamSubmissionRecord:
    return DownstreamSubmissionRecord(
        idempotency_key=read_row_value(row, "idempotency_key"),
        request_fingerprint=read_row_value(row, "request_fingerprint"),
        resource_type=DownstreamSubmissionResourceType(read_row_value(row, "resource_type")),
        resource_id=read_row_value(row, "resource_id"),
        target=ConversionTarget(read_row_value(row, "target")),
        source_authority=SourceSystem(read_row_value(row, "source_authority")),
        status=DownstreamSubmissionPosture(read_row_value(row, "status")),
        downstream_failure_reason=read_row_value(row, "downstream_failure_reason"),
        correlation_id=read_row_value(row, "correlation_id"),
        trace_id=read_row_value(row, "trace_id"),
        submitted_at_utc=read_row_value(row, "submitted_at_utc"),
        support_reference=read_row_value(row, "support_reference"),
        attempt_count=read_row_value(row, "attempt_count"),
        updated_at_utc=read_row_value(row, "updated_at_utc"),
        lease_owner=read_row_value(row, "lease_owner"),
        lease_attempt_id=read_row_value(row, "lease_attempt_id"),
        lease_expires_at_utc=read_row_value(row, "lease_expires_at_utc"),
        audit_history=tuple(
            downstream_submission_audit_from_json(item)
            for item in _audit_payloads(read_row_value(row, "audit_json"))
        ),
        owner_receipt=_owner_receipt_from_json(read_row_value(row, "owner_receipt_json")),
    )


def downstream_submission_audit_to_json(entry: DownstreamSubmissionAuditEntry) -> dict[str, Any]:
    return {
        "auditId": entry.audit_id,
        "action": entry.action.value,
        "actorSubject": entry.actor_subject,
        "previousPosture": entry.previous_posture.value if entry.previous_posture else None,
        "currentPosture": entry.current_posture.value,
        "occurredAtUtc": entry.occurred_at_utc.isoformat(),
        "reason": entry.reason,
        "changeReference": entry.change_reference,
    }


def downstream_submission_audit_from_json(
    payload: Mapping[str, Any],
) -> DownstreamSubmissionAuditEntry:
    previous = payload.get("previousPosture")
    return DownstreamSubmissionAuditEntry(
        audit_id=_required_string(payload, "auditId"),
        action=DownstreamSubmissionAuditAction(_required_string(payload, "action")),
        actor_subject=_required_string(payload, "actorSubject"),
        previous_posture=(DownstreamSubmissionPosture(str(previous)) if previous else None),
        current_posture=DownstreamSubmissionPosture(_required_string(payload, "currentPosture")),
        occurred_at_utc=decode_datetime(payload.get("occurredAtUtc")),
        reason=_optional_string(payload, "reason"),
        change_reference=_optional_string(payload, "changeReference"),
    )


def _load_by_idempotency_key(
    cursor: PostgresCursor,
    idempotency_key: str,
    *,
    for_update: bool,
) -> DownstreamSubmissionRecord | None:
    return _load_one(
        cursor,
        marker="downstream-submission-by-idempotency",
        predicate="idempotency_key = %s",
        value=idempotency_key,
        for_update=for_update,
    )


def _load_by_support_reference(
    cursor: PostgresCursor,
    support_reference: str,
    *,
    for_update: bool,
) -> DownstreamSubmissionRecord | None:
    return _load_one(
        cursor,
        marker="downstream-submission-by-support-reference",
        predicate="support_reference = %s",
        value=support_reference,
        for_update=for_update,
    )


def _load_one(
    cursor: PostgresCursor,
    *,
    marker: str,
    predicate: str,
    value: str,
    for_update: bool,
) -> DownstreamSubmissionRecord | None:
    lock = "FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        /* lotus-idea {marker} */
        SELECT {DOWNSTREAM_SUBMISSION_COLUMNS}
        FROM idea_downstream_submission
        WHERE {predicate}
        {lock}
        """,
        (value,),
    )
    rows = cursor.fetchall()
    return downstream_submission_from_row(rows[0]) if rows else None


def _update_mutable_submission_state(
    cursor: PostgresCursor,
    record: DownstreamSubmissionRecord,
) -> None:
    cursor.execute(
        f"""
        /* lotus-idea downstream-submission-state-update */
        UPDATE idea_downstream_submission
        SET status = %s,
            downstream_failure_reason = %s,
            updated_at_utc = %s,
            audit_json = %s
            , owner_receipt_json = %s
        WHERE idempotency_key = %s
          AND lease_attempt_id IS NOT DISTINCT FROM %s
        RETURNING {DOWNSTREAM_SUBMISSION_COLUMNS}
        """,
        (
            record.status.value,
            record.downstream_failure_reason,
            record.updated_at_utc,
            Jsonb([downstream_submission_audit_to_json(entry) for entry in record.audit_history]),
            Jsonb(_owner_receipt_to_json(record.owner_receipt)) if record.owner_receipt else None,
            record.idempotency_key,
            record.lease_attempt_id,
        ),
    )
    if not cursor.fetchall():
        raise RuntimeError("downstream submission state update lost its lease")


def _owner_receipt_to_json(receipt: DownstreamSubmissionOwnerReceipt) -> dict[str, Any]:
    return {
        "ownerAuthority": receipt.owner_authority.value,
        "ownerRequestId": receipt.owner_request_id,
        "ownerRealizationId": receipt.owner_realization_id,
        "ownerWorkId": receipt.owner_work_id,
        "sourceEventVersion": receipt.source_event_version,
        "sourceEvidenceFingerprint": receipt.source_evidence_fingerprint,
        "reportMaterialization": (
            _report_materialization_to_json(receipt.report_materialization)
            if receipt.report_materialization is not None
            else None
        ),
    }


def _report_materialization_to_json(
    evidence: ReportMaterializationReceiptEvidence,
) -> dict[str, Any]:
    return {
        "status": evidence.status,
        "materializationStatus": evidence.materialization_status,
        "statusUrl": evidence.status_url,
        "reportEvidencePackId": evidence.report_evidence_pack_id,
        "conversionIntentId": evidence.conversion_intent_id,
        "candidateId": evidence.candidate_id,
        "evidencePacketId": evidence.evidence_packet_id,
        "createsReportJob": evidence.creates_report_job,
        "createsRenderedOutput": evidence.creates_rendered_output,
        "createsArchiveRecord": evidence.creates_archive_record,
        "renderJobId": evidence.render_job_id,
        "archiveDocumentId": evidence.archive_document_id,
        "supportabilityStatus": evidence.supportability_status,
        "remainingBlockers": list(evidence.remaining_blockers),
    }


def _owner_receipt_from_json(value: Any) -> DownstreamSubmissionOwnerReceipt | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("owner_receipt_json must be an object")
    version = value.get("sourceEventVersion")
    if version is not None and (not isinstance(version, int) or isinstance(version, bool)):
        raise ValueError("owner receipt sourceEventVersion must be an integer when present")
    report_materialization = _report_materialization_from_json(value.get("reportMaterialization"))
    return DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem(_required_string(value, "ownerAuthority")),
        owner_request_id=_required_string(value, "ownerRequestId"),
        owner_realization_id=_required_string(value, "ownerRealizationId"),
        owner_work_id=_optional_string(value, "ownerWorkId"),
        source_event_version=version,
        source_evidence_fingerprint=_required_string(value, "sourceEvidenceFingerprint"),
        report_materialization=report_materialization,
    )


def _report_materialization_from_json(
    value: Any,
) -> ReportMaterializationReceiptEvidence | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("reportMaterialization must be an object")
    blockers = value.get("remainingBlockers")
    if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes, bytearray)):
        raise ValueError("remainingBlockers must be an array")
    normalized_blockers: list[str] = []
    for blocker in blockers:
        if not isinstance(blocker, str) or not blocker.strip():
            raise ValueError("remainingBlockers must contain non-blank strings")
        normalized_blockers.append(blocker)
    return ReportMaterializationReceiptEvidence(
        status=_required_string(value, "status"),
        materialization_status=_required_string(value, "materializationStatus"),
        status_url=_required_string(value, "statusUrl"),
        report_evidence_pack_id=_required_string(value, "reportEvidencePackId"),
        conversion_intent_id=_required_string(value, "conversionIntentId"),
        candidate_id=_required_string(value, "candidateId"),
        evidence_packet_id=_required_string(value, "evidencePacketId"),
        creates_report_job=_required_bool(value, "createsReportJob"),
        creates_rendered_output=_required_bool(value, "createsRenderedOutput"),
        creates_archive_record=_required_bool(value, "createsArchiveRecord"),
        render_job_id=_optional_string(value, "renderJobId"),
        archive_document_id=_optional_string(value, "archiveDocumentId"),
        supportability_status=_required_string(value, "supportabilityStatus"),
        remaining_blockers=tuple(normalized_blockers),
    )


def _audit_payloads(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("audit_json must be an array")
    payloads: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("audit_json entries must be objects")
        payloads.append(item)
    return tuple(payloads)


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-blank string")
    return value


def _required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value
