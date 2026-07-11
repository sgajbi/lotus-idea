from __future__ import annotations

from typing import Any, Sequence


def candidate_detail_rows(
    connection: Any,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    table_name = _table_from_select(query)
    if "where conversion_intent_id = any(%s)" in query:
        intent_ids = set(params[0])
        return [
            dict(row)
            for row in connection.rows[table_name]
            if row["conversion_intent_id"] in intent_ids
        ]
    if "candidate_id = %s" in query:
        candidate_id = params[0]
        rows = [
            dict(row)
            for row in connection.rows[table_name]
            if row.get("candidate_id") == candidate_id
        ]
        return (
            _active_candidate_rows(connection, rows)
            if "join idea_data_lifecycle" in query
            else rows
        )
    raise AssertionError(f"unexpected candidate detail query: {query}")


def downstream_lookup_rows(
    connection: Any,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    table_name = _table_from_select(query)
    lookup_value = params[0]
    if "conversion_intent_id = %s" in query:
        rows = [
            dict(row)
            for row in connection.rows[table_name]
            if row["conversion_intent_id"] == lookup_value
        ]
        return _active_candidate_rows(connection, rows)
    if "report_evidence_pack_id = %s" in query:
        rows = [
            dict(row)
            for row in connection.rows[table_name]
            if row["report_evidence_pack_id"] == lookup_value
        ]
        return _active_candidate_rows(connection, rows)
    if "where idempotency_key = %s" in query:
        return [
            dict(row)
            for row in connection.rows[table_name]
            if row["idempotency_key"] == lookup_value
        ]
    raise AssertionError(f"unexpected downstream lookup query: {query}")


def _active_candidate_rows(
    connection: Any,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    controls = {row["candidate_id"]: row for row in connection.rows["idea_data_lifecycle_control"]}
    return [
        row
        for row in rows
        if (control := controls.get(row.get("candidate_id"))) is not None
        and (control.get("held_from_state") or control["state"]) == "active"
    ]


def idempotency_lookup_rows(
    connection: Any,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    table_name = _table_from_select(query)
    idempotency_key = params[0]
    if "where idempotency_key = %s" in query:
        return [
            dict(row)
            for row in connection.rows[table_name]
            if row["idempotency_key"] == idempotency_key
        ]
    raise AssertionError(f"unexpected idempotency lookup query: {query}")


def _table_from_select(query: str) -> str:
    for table_name in (
        "idea_candidate_record",
        "idea_idempotency_record",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_conversion_outcome",
        "idea_report_evidence_pack_request",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
    ):
        if f" from {table_name}" in query:
            return table_name
    raise AssertionError(f"unknown select table: {query}")
