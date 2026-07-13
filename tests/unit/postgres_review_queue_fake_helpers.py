from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, Sequence

from app.domain import (
    IdeaLifecycleStatus,
    QueueExclusionReason,
    ReviewPosture,
    candidate_state_is_compatible,
)


class FakeReviewQueueConnection(Protocol):
    rows: dict[str, list[dict[str, Any]]]


def review_queue_count_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    visible_rows = _review_queue_visible_rows(
        connection,
        params[0],
        required_posture=params[1],
    )
    rows = _review_queue_ordered_rows(connection, query, params)
    return [
        {
            "total_reviewable_item_count": len(rows),
            "total_excluded_candidate_count": len(visible_rows) - len(rows),
            "snapshot_fingerprint": _review_queue_snapshot_fingerprint(visible_rows),
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


def review_queue_readiness_summary_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    scope_fields = tuple(
        field_name
        for field_name in ("tenant_id", "book_id", "portfolio_id", "client_id")
        if f"->>'{field_name}'" in query
    )
    evaluated_at_utc = params[0]
    required_posture = params[1]
    scope_values = {
        field_name: set(values)
        for field_name, values in zip(scope_fields, params[2 : 2 + len(scope_fields)], strict=True)
    }
    offset = 2 + len(scope_fields)
    suppressed_posture = params[offset]
    expired_status = params[offset + 1]
    closed_status = params[offset + 2]
    rejected_status = params[offset + 3]
    blocked_supportability = params[offset + 4]
    rankable_score_policy_versions = set(params[offset + 5])
    lifecycle_statuses = set(params[offset + 6])
    exclusion_counts = {reason.value: 0 for reason in QueueExclusionReason}
    eligible_rows: list[dict[str, Any]] = []
    scored_candidate_count = 0
    unscored_candidate_count = 0
    visible_rows = _review_queue_visible_rows(
        connection,
        evaluated_at_utc,
        required_posture=required_posture,
    )
    for row in visible_rows:
        candidate_json = row["candidate_json"]
        if candidate_json.get("score") is None:
            unscored_candidate_count += 1
        else:
            scored_candidate_count += 1
        exclusion_reason = _review_queue_row_exclusion_reason(
            row,
            lifecycle_statuses=lifecycle_statuses,
            suppressed_posture=suppressed_posture,
            expired_status=expired_status,
            closed_status=closed_status,
            rejected_status=rejected_status,
            blocked_supportability=blocked_supportability,
            rankable_score_policy_versions=rankable_score_policy_versions,
            scope_values=scope_values,
        )
        if exclusion_reason is None:
            eligible_rows.append(row)
        else:
            exclusion_counts[exclusion_reason] += 1

    winners_by_signal: dict[str, dict[str, Any]] = {}
    for row in sorted(eligible_rows, key=_review_queue_source_signal_sort_key):
        signal_key = _source_signal_key(row)
        winners_by_signal.setdefault(signal_key, row)
    duplicate_count = len(eligible_rows) - len(winners_by_signal)
    exclusion_counts[QueueExclusionReason.DUPLICATE.value] = duplicate_count
    return [
        {
            "candidate_snapshot_count": len(visible_rows),
            "reviewable_item_count": len(winners_by_signal),
            "excluded_candidate_count": sum(exclusion_counts.values()),
            "scored_candidate_count": scored_candidate_count,
            "unscored_candidate_count": unscored_candidate_count,
            **exclusion_counts,
        }
    ]


def _review_queue_ordered_rows(
    connection: FakeReviewQueueConnection,
    query: str,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    evaluated_at_utc = params[0]
    required_posture = params[1]
    lifecycle_statuses = set(params[2])
    suppressed_posture = params[3]
    rankable_score_policy_versions = set(params[4])
    blocked_supportability = params[5]
    scope_fields = tuple(
        field_name
        for field_name in ("tenant_id", "book_id", "portfolio_id", "client_id")
        if f"->>'{field_name}'" in query
    )
    scope_values = {
        field_name: set(values) for field_name, values in zip(scope_fields, params[6:], strict=True)
    }
    eligible_rows = [
        row
        for row in _review_queue_visible_rows(
            connection,
            evaluated_at_utc,
            required_posture=required_posture,
        )
        if _review_queue_row_is_eligible(
            row,
            lifecycle_statuses=lifecycle_statuses,
            suppressed_posture=suppressed_posture,
            blocked_supportability=blocked_supportability,
            rankable_score_policy_versions=rankable_score_policy_versions,
            scope_values=scope_values,
        )
    ]
    winners_by_signal: dict[str, dict[str, Any]] = {}
    for row in sorted(eligible_rows, key=_review_queue_source_signal_sort_key):
        signal_key = _source_signal_key(row)
        winners_by_signal.setdefault(signal_key, row)
    return sorted(winners_by_signal.values(), key=_review_queue_sort_key)


def _review_queue_visible_rows(
    connection: FakeReviewQueueConnection,
    evaluated_at_utc: datetime,
    *,
    required_posture: str | None = None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in connection.rows["idea_candidate_record"]
        if datetime.fromisoformat(row["candidate_json"]["created_at_utc"]) <= evaluated_at_utc
        and (required_posture is None or row["review_posture"] == required_posture)
    ]


def _review_queue_snapshot_fingerprint(rows: list[dict[str, Any]]) -> str:
    material = "".join(
        hashlib.md5(  # noqa: S324 - mirrors PostgreSQL's non-security change fingerprint
            (
                f"{row['candidate_id']}|{row['evidence_hash']}|"
                f"{json.dumps(row['candidate_json'], sort_keys=True, separators=(',', ':'))}"
            ).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        for row in sorted(rows, key=lambda item: item["candidate_id"])
    )
    return hashlib.md5(material.encode("utf-8"), usedforsecurity=False).hexdigest()


def _review_queue_row_exclusion_reason(
    row: dict[str, Any],
    *,
    lifecycle_statuses: set[str],
    suppressed_posture: str,
    expired_status: str,
    closed_status: str,
    rejected_status: str,
    blocked_supportability: str,
    rankable_score_policy_versions: set[str],
    scope_values: dict[str, set[str]],
) -> str | None:
    candidate_json = row["candidate_json"]
    access_scope = candidate_json.get("access_scope")
    if scope_values and access_scope is None:
        return QueueExclusionReason.ACCESS_SCOPE_MISMATCH.value
    for field_name, expected_values in scope_values.items():
        if access_scope is None or access_scope.get(field_name) not in expected_values:
            return QueueExclusionReason.ACCESS_SCOPE_MISMATCH.value
    if not _review_queue_row_has_compatible_state(row):
        return QueueExclusionReason.INVALID_STATE.value
    if row["review_posture"] == suppressed_posture:
        return QueueExclusionReason.SUPPRESSED.value
    if candidate_json.get("suppression_reason") is not None:
        return QueueExclusionReason.SUPPRESSED.value
    if row["lifecycle_status"] == expired_status:
        return QueueExclusionReason.EXPIRED.value
    if row["lifecycle_status"] == closed_status:
        return QueueExclusionReason.CLOSED.value
    if row["lifecycle_status"] == rejected_status:
        return QueueExclusionReason.REJECTED.value
    if candidate_json["evidence_packet"]["supportability"] == blocked_supportability:
        return QueueExclusionReason.UNSUPPORTED_EVIDENCE.value
    if candidate_json.get("score") is None:
        return QueueExclusionReason.UNSCORED.value
    if candidate_json["score"].get("policy_version") not in rankable_score_policy_versions:
        return QueueExclusionReason.UNRANKABLE_SCORE_POLICY.value
    if row["lifecycle_status"] not in lifecycle_statuses:
        return QueueExclusionReason.NON_REVIEWABLE_STATUS.value
    return None


def _review_queue_row_is_eligible(
    row: dict[str, Any],
    *,
    lifecycle_statuses: set[str],
    suppressed_posture: str,
    blocked_supportability: str,
    rankable_score_policy_versions: set[str],
    scope_values: dict[str, set[str]],
) -> bool:
    candidate_json = row["candidate_json"]
    if not _review_queue_row_has_compatible_state(row):
        return False
    if row["lifecycle_status"] not in lifecycle_statuses:
        return False
    if row["review_posture"] == suppressed_posture:
        return False
    if candidate_json.get("suppression_reason") is not None:
        return False
    if candidate_json.get("score") is None:
        return False
    if candidate_json["score"].get("policy_version") not in rankable_score_policy_versions:
        return False
    if candidate_json["evidence_packet"]["supportability"] == blocked_supportability:
        return False
    access_scope = candidate_json.get("access_scope")
    for field_name, expected_values in scope_values.items():
        if access_scope is None or access_scope.get(field_name) not in expected_values:
            return False
    return True


def _review_queue_row_has_compatible_state(row: dict[str, Any]) -> bool:
    try:
        lifecycle_status = IdeaLifecycleStatus(row["lifecycle_status"])
        review_posture = ReviewPosture(row["review_posture"])
    except ValueError:
        return False
    return candidate_state_is_compatible(lifecycle_status, review_posture)


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
