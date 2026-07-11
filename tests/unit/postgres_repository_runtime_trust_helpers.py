from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def runtime_trust_telemetry_summary_rows(
    rows: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    candidate_rows = _active_candidate_rows(rows)
    active_candidate_ids = {row["candidate_id"] for row in candidate_rows}
    source_refs = _runtime_trust_source_refs(rows)
    current_source_refs = [
        source_ref for source_ref in source_refs if source_ref.get("freshness") == "current"
    ]
    generated_at_values = [
        str(source_ref["generated_at_utc"])
        for source_ref in source_refs
        if source_ref.get("generated_at_utc") is not None
    ]
    latest_generated_at = max(generated_at_values, default=None)
    return [
        {
            "candidate_snapshot_count": len(candidate_rows),
            "current_source_ref_count": len(current_source_refs),
            "stale_or_unavailable_source_ref_count": len(source_refs) - len(current_source_refs),
            "source_batch_evidence_available": bool(source_refs),
            "lineage_materialized": bool(candidate_rows)
            and all(_candidate_lineage_materialized(row) for row in candidate_rows),
            "data_quality_status": _runtime_trust_data_quality_status(source_refs),
            "latest_source_generated_at_utc": latest_generated_at,
            "source_as_of_dates": sorted(
                {
                    str(source_ref["as_of_date"])
                    for source_ref in source_refs
                    if source_ref.get("as_of_date")
                }
            ),
            "review_decision_count": _candidate_row_count(
                rows["idea_review_decision"], active_candidate_ids
            ),
            "feedback_event_count": _candidate_row_count(
                rows["idea_feedback_event"], active_candidate_ids
            ),
            "conversion_intent_count": _candidate_row_count(
                rows["idea_conversion_intent"], active_candidate_ids
            ),
            "conversion_outcome_count": _active_outcome_count(rows, active_candidate_ids),
            "report_evidence_pack_count": _candidate_row_count(
                rows["idea_report_evidence_pack_request"], active_candidate_ids
            ),
            "retention_expired_count": sum(
                1
                for control in rows["idea_data_lifecycle_control"]
                if control["state"] == "active"
                and control["retention_expires_at_utc"] <= datetime.now(UTC)
            ),
            "lifecycle_control_missing_count": len(rows["idea_candidate_record"])
            - len(rows["idea_data_lifecycle_control"]),
        }
    ]


def runtime_trust_telemetry_count_rows(
    rows: dict[str, list[dict[str, Any]]],
    source_ref_key: str,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for source_ref in _runtime_trust_source_refs(rows):
        value = source_ref.get(source_ref_key)
        if value is not None:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def candidate_json_count_rows(
    rows: dict[str, list[dict[str, Any]]],
    path: tuple[str, ...],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in _active_candidate_rows(rows):
        value: Any = row["candidate_json"]
        for key in path:
            value = value[key]
        counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def table_count_rows(
    rows: dict[str, list[dict[str, Any]]],
    table_name: str,
    column_name: str,
    *,
    active_candidates_only: bool = False,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    selected_rows = _active_candidate_rows(rows) if active_candidates_only else rows[table_name]
    for row in selected_rows:
        value = row.get(column_name)
        if value is not None:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def _runtime_trust_source_refs(rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    source_refs: list[dict[str, Any]] = []
    for row in _active_candidate_rows(rows):
        candidate_json = row["candidate_json"]
        source_refs.extend(candidate_json["evidence_packet"]["source_refs"])
    return source_refs


def _active_candidate_rows(
    rows: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    controls = {row["candidate_id"]: row for row in rows["idea_data_lifecycle_control"]}
    return [
        row
        for row in rows["idea_candidate_record"]
        if (control := controls.get(row["candidate_id"])) is not None
        and (control.get("held_from_state") or control["state"]) == "active"
    ]


def _candidate_row_count(records: list[dict[str, Any]], active_candidate_ids: set[str]) -> int:
    return sum(1 for record in records if record["candidate_id"] in active_candidate_ids)


def _active_outcome_count(
    rows: dict[str, list[dict[str, Any]]], active_candidate_ids: set[str]
) -> int:
    active_intents = {
        row["conversion_intent_id"]
        for row in rows["idea_conversion_intent"]
        if row["candidate_id"] in active_candidate_ids
    }
    return sum(
        1
        for outcome in rows["idea_conversion_outcome"]
        if outcome["conversion_intent_id"] in active_intents
    )


def _candidate_lineage_materialized(row: dict[str, Any]) -> bool:
    lineage_ref = row["candidate_json"]["evidence_packet"]["lineage_ref"]
    return bool(lineage_ref.get("lineage_id") and lineage_ref.get("source_refs"))


def _runtime_trust_data_quality_status(source_refs: list[dict[str, Any]]) -> str:
    if not source_refs:
        return "quality_unknown"
    if all(source_ref.get("data_quality_status") == "complete" for source_ref in source_refs):
        return "quality_passed"
    return "quality_warning"
