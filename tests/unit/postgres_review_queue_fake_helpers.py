from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, Sequence


class FakeReviewQueueConnection(Protocol):
    rows: dict[str, list[dict[str, Any]]]


def review_queue_count_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    rows = _review_queue_ordered_rows(connection, query, params)
    return [
        {
            "total_reviewable_item_count": len(rows),
            "total_excluded_candidate_count": (
                len(connection.rows["idea_candidate_record"]) - len(rows)
            ),
        }
    ]


def review_queue_page_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    limit = int(params[-2])
    offset = int(params[-1])
    rows = _review_queue_ordered_rows(connection, query, params[:-2])
    return [dict(row) for row in rows[offset : offset + limit]]


def _review_queue_ordered_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    lifecycle_statuses = set(params[0])
    suppressed_posture = params[1]
    blocked_supportability = params[2]
    scope_fields = tuple(
        field_name
        for field_name in ("tenant_id", "book_id", "portfolio_id", "client_id")
        if f"->>'{field_name}'" in query
    )
    scope_values = {
        field_name: set(values) for field_name, values in zip(scope_fields, params[3:], strict=True)
    }
    eligible_rows = [
        row
        for row in connection.rows["idea_candidate_record"]
        if _review_queue_row_is_eligible(
            row,
            lifecycle_statuses=lifecycle_statuses,
            suppressed_posture=suppressed_posture,
            blocked_supportability=blocked_supportability,
            scope_values=scope_values,
        )
    ]
    winners_by_signal: dict[str, dict[str, Any]] = {}
    for row in sorted(eligible_rows, key=_review_queue_source_signal_sort_key):
        signal_key = _source_signal_key(row)
        winners_by_signal.setdefault(signal_key, row)
    return sorted(winners_by_signal.values(), key=_review_queue_sort_key)


def _review_queue_row_is_eligible(
    row: dict[str, Any],
    *,
    lifecycle_statuses: set[str],
    suppressed_posture: str,
    blocked_supportability: str,
    scope_values: dict[str, set[str]],
) -> bool:
    candidate_json = row["candidate_json"]
    if row["lifecycle_status"] not in lifecycle_statuses:
        return False
    if row["review_posture"] == suppressed_posture:
        return False
    if candidate_json.get("suppression_reason") is not None:
        return False
    if candidate_json.get("score") is None:
        return False
    if candidate_json["evidence_packet"]["supportability"] == blocked_supportability:
        return False
    access_scope = candidate_json.get("access_scope")
    for field_name, expected_values in scope_values.items():
        if access_scope is None or access_scope.get(field_name) not in expected_values:
            return False
    return True


def _review_queue_source_signal_sort_key(
    row: dict[str, Any],
) -> tuple[str, Decimal, str, str]:
    score = Decimal(str(row["candidate_json"]["score"]["score"]))
    return (
        _source_signal_key(row),
        -score,
        row["candidate_json"]["created_at_utc"],
        row["candidate_id"],
    )


def _review_queue_sort_key(row: dict[str, Any]) -> tuple[Decimal, str, str]:
    score = Decimal(str(row["candidate_json"]["score"]["score"]))
    return (-score, row["candidate_json"]["created_at_utc"], row["candidate_id"])


def _source_signal_key(row: dict[str, Any]) -> str:
    signals = row["candidate_json"].get("source_signal_ids") or [row["candidate_id"]]
    return ",".join(sorted(str(signal) for signal in signals))
