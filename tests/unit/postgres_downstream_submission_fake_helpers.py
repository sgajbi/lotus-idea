from __future__ import annotations

from typing import Any, Sequence

from tests.unit.postgres_repository_mutation_fake_helpers import row_for_insert


def execute_downstream_submission_query(
    cursor: Any,
    query: str,
    params: Sequence[Any] | None,
) -> bool:
    connection = cursor.connection
    rows = connection.rows["idea_downstream_submission"]

    if query.startswith("/* lotus-idea downstream-submission-claim */"):
        assert params is not None
        connection.begin_write()
        if connection.fail_on_insert == "idea_downstream_submission":
            raise RuntimeError("insert failed for idea_downstream_submission")
        if any(row["idempotency_key"] == params[0] for row in rows):
            cursor._rows = []
            return True
        row = row_for_insert("idea_downstream_submission", params)
        rows.append(row)
        cursor._rows = [dict(row)]
        return True

    if query.startswith("/* lotus-idea downstream-submission-by-idempotency */"):
        assert params is not None
        cursor._rows = [
            dict(row) for row in rows if row["idempotency_key"] == params[0]
        ]
        return True

    if query.startswith("/* lotus-idea downstream-submission-by-support-reference */"):
        assert params is not None
        cursor._rows = [
            dict(row) for row in rows if row["support_reference"] == params[0]
        ]
        return True

    if query.startswith("/* lotus-idea downstream-submission-reconciliation-list */"):
        assert params is not None
        first_posture, second_posture, limit = params
        pending = [
            dict(row)
            for row in rows
            if row["status"] in {first_posture, second_posture}
        ]
        pending.sort(key=lambda row: (row["updated_at_utc"], row["support_reference"]))
        cursor._rows = pending[:limit]
        return True

    if query.startswith("/* lotus-idea downstream-submission-state-update */"):
        assert params is not None
        connection.begin_write()
        if connection.fail_on_update == "idea_downstream_submission":
            raise RuntimeError("update failed for idea_downstream_submission")
        status, failure_reason, updated_at_utc, audit_json, key, lease_attempt_id = params
        for row in rows:
            if row["idempotency_key"] != key:
                continue
            if row["lease_attempt_id"] != lease_attempt_id:
                cursor._rows = []
                return True
            row.update(
                status=status,
                downstream_failure_reason=failure_reason,
                updated_at_utc=updated_at_utc,
                audit_json=_unwrap_jsonb(audit_json),
            )
            cursor._rows = [dict(row)]
            return True
        cursor._rows = []
        return True

    return False


def _unwrap_jsonb(value: Any) -> Any:
    return value.obj if hasattr(value, "obj") else value
