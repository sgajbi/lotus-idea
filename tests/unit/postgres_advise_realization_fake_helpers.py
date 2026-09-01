from __future__ import annotations

from typing import Any, Sequence


def execute_advise_realization_query(
    cursor: Any,
    query: str,
    params: Sequence[Any] | None,
) -> bool:
    connection = cursor.connection
    if query.startswith("/* lotus-idea advise-realization-submission-lock */"):
        assert params is not None
        cursor._rows = [
            dict(row)
            for row in connection.rows["idea_downstream_submission"]
            if row["support_reference"] == params[0]
        ]
        return True
    if query.startswith("/* lotus-idea advise-realization-history-load */"):
        assert params is not None
        cursor._rows = [
            dict(row)
            for row in connection.rows["idea_advise_realization_history"]
            if row["support_reference"] == params[0]
        ]
        return True
    if query.startswith("/* lotus-idea advise-realization-history-store */"):
        assert params is not None
        connection.begin_write()
        support_reference, realization_id, intake_id, version, history_json, persisted_at = params
        history = _unwrap_jsonb(history_json)
        rows = connection.rows["idea_advise_realization_history"]
        existing = next(
            (row for row in rows if row["support_reference"] == support_reference),
            None,
        )
        if existing is None:
            stored = {
                "support_reference": support_reference,
                "realization_id": realization_id,
                "intake_id": intake_id,
                "current_source_event_version": version,
                "history_json": history,
                "persisted_at_utc": persisted_at,
            }
            rows.append(stored)
            cursor._rows = [dict(stored)]
            return True
        if (
            existing["realization_id"] != realization_id
            or existing["intake_id"] != intake_id
            or existing["current_source_event_version"] >= version
        ):
            cursor._rows = []
            return True
        existing.update(
            current_source_event_version=version,
            history_json=history,
            persisted_at_utc=persisted_at,
        )
        cursor._rows = [dict(existing)]
        return True
    return False


def _unwrap_jsonb(value: Any) -> Any:
    return value.obj if hasattr(value, "obj") else value
