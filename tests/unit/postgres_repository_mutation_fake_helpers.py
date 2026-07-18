from __future__ import annotations

from collections.abc import Callable
from typing import Any, Sequence

RowBuilder = Callable[[Sequence[Any]], dict[str, Any]]


def row_for_insert(table_name: str, params: Sequence[Any]) -> dict[str, Any]:
    values = [_unwrap_jsonb(value) for value in params]
    return _ROW_BUILDERS[table_name](values)


def _candidate_record_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "candidate_id",
            "family",
            "lifecycle_status",
            "review_posture",
            "evidence_packet_id",
            "evidence_hash",
            "candidate_json",
            "persisted_at_utc",
            "updated_at_utc",
        ),
        values,
    )


def _idempotency_record_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "idempotency_key",
            "operation_name",
            "payload_hash",
            "candidate_id",
            "created_at_utc",
        ),
        values,
    )


def _lifecycle_history_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "lifecycle_history_id",
            "candidate_id",
            "source_status",
            "target_status",
            "actor_subject",
            "changed_at_utc",
        ),
        values,
    )


def _audit_event_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "audit_event_id",
            "candidate_id",
            "event_type",
            "actor_subject",
            "outcome",
            "attributes_json",
            "occurred_at_utc",
        ),
        values,
    )


def _outbox_event_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "outbox_event_id",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            "schema_version",
            "payload_json",
            "status",
            "occurred_at_utc",
            "idempotency_fingerprint",
            "correlation_id",
            "trace_id",
            "causation_id",
            "lineage_origin",
            "published_at_utc",
            "failure_reason",
            "retry_count",
            "first_failed_at_utc",
            "last_failed_at_utc",
            "next_attempt_at_utc",
            "lease_owner",
            "lease_attempt_id",
            "lease_expires_at_utc",
        ),
        values,
    )


def _review_decision_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "review_decision_id",
            "candidate_id",
            "action",
            "actor_subject",
            "decision_json",
            "decided_at_utc",
        ),
        values,
    )


def _feedback_event_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "feedback_event_id",
            "candidate_id",
            "actor_subject",
            "feedback_json",
            "recorded_at_utc",
        ),
        values,
    )


def _conversion_intent_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "conversion_intent_id",
            "candidate_id",
            "target",
            "actor_subject",
            "intent_json",
            "requested_at_utc",
        ),
        values,
    )


def _conversion_outcome_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "conversion_outcome_id",
            "conversion_intent_id",
            "source_system",
            "status",
            "source_event_version",
            "supersedes_conversion_outcome_id",
            "correction_reason",
            "actor_subject",
            "outcome_json",
            "recorded_at_utc",
        ),
        values,
    )


def _report_evidence_pack_request_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "report_evidence_pack_id",
            "candidate_id",
            "conversion_intent_id",
            "purpose",
            "evidence_hash",
            "evidence_pack_json",
            "requested_at_utc",
        ),
        values,
    )


def _downstream_submission_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "idempotency_key",
            "request_fingerprint",
            "resource_type",
            "resource_id",
            "target",
            "source_authority",
            "status",
            "downstream_failure_reason",
            "correlation_id",
            "trace_id",
            "submitted_at_utc",
            "support_reference",
            "attempt_count",
            "updated_at_utc",
            "lease_owner",
            "lease_attempt_id",
            "lease_expires_at_utc",
            "audit_json",
        ),
        values,
    )


def _ai_explanation_lineage_row(values: Sequence[Any]) -> dict[str, Any]:
    return _row_from_columns(
        (
            "ai_explanation_request_id",
            "candidate_id",
            "evidence_packet_id",
            "evidence_content_hash",
            "workflow_pack_id",
            "workflow_pack_version",
            "purpose",
            "posture",
            "verifier_outcome",
            "fallback_used",
            "fallback_reason",
            "output_integrity_version",
            "output_content_digest",
            "lineage_hash",
            "execution_provenance_posture",
            "lotus_ai_run_id",
            "lotus_ai_replay_nonce",
            "lotus_ai_attestation_key_id",
            "provider_retention_confirmation_id",
            "provider_retention_confirmation_ref",
            "provider_retention_replay_nonce",
            "lineage_json",
            "requested_at_utc",
            "evaluated_at_utc",
        ),
        values,
    )


def _row_from_columns(
    columns: Sequence[str],
    values: Sequence[Any],
) -> dict[str, Any]:
    return dict(zip(columns, values, strict=True))


_ROW_BUILDERS: dict[str, RowBuilder] = {
    "idea_candidate_record": _candidate_record_row,
    "idea_idempotency_record": _idempotency_record_row,
    "idea_lifecycle_history": _lifecycle_history_row,
    "idea_audit_event": _audit_event_row,
    "idea_outbox_event": _outbox_event_row,
    "idea_review_decision": _review_decision_row,
    "idea_feedback_event": _feedback_event_row,
    "idea_conversion_intent": _conversion_intent_row,
    "idea_conversion_outcome": _conversion_outcome_row,
    "idea_report_evidence_pack_request": _report_evidence_pack_request_row,
    "idea_downstream_submission": _downstream_submission_row,
    "idea_ai_explanation_lineage": _ai_explanation_lineage_row,
}


def update_candidate_record_row(
    rows: dict[str, list[dict[str, Any]]],
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    (
        family,
        lifecycle_status,
        review_posture,
        evidence_packet_id,
        evidence_hash,
        candidate_json,
        updated_at_utc,
        candidate_id,
        expected_updated_at_utc,
    ) = [_unwrap_jsonb(value) for value in params]
    for row in rows["idea_candidate_record"]:
        if row["candidate_id"] != candidate_id:
            continue
        if row["updated_at_utc"] != expected_updated_at_utc:
            return []
        row["family"] = family
        row["lifecycle_status"] = lifecycle_status
        row["review_posture"] = review_posture
        row["evidence_packet_id"] = evidence_packet_id
        row["evidence_hash"] = evidence_hash
        row["candidate_json"] = candidate_json
        row["updated_at_utc"] = updated_at_utc
        return [dict(row)]
    return []


def _unwrap_jsonb(value: Any) -> Any:
    if hasattr(value, "obj"):
        return value.obj
    return value
