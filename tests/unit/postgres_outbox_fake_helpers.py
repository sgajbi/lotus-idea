from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Sequence

from app.domain import OutboxEventStatus


class FakeOutboxConnection(Protocol):
    rows: dict[str, list[dict[str, Any]]]


def claim_outbox_event_rows(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    max_retry_count = params[2]
    claimed_at_utc: datetime = params[3]
    limit = params[6]
    lease_owner = params[8]
    lease_attempt_id = params[9]
    lease_expires_at_utc = params[10]
    candidates = [
        row
        for row in connection.rows["idea_outbox_event"]
        if _delivery_ready(row, max_retry_count=max_retry_count, claimed_at_utc=claimed_at_utc)
    ]
    candidates.sort(key=lambda row: (row["occurred_at_utc"], row["outbox_event_id"]))
    claimed = candidates[:limit]
    for row in claimed:
        row["status"] = OutboxEventStatus.LEASED.value
        row["next_attempt_at_utc"] = None
        row["lease_owner"] = lease_owner
        row["lease_attempt_id"] = lease_attempt_id
        row["lease_expires_at_utc"] = lease_expires_at_utc
    return [dict(row) for row in claimed]


def outbox_delivery_ready_rows(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    max_retry_count = params[2]
    evaluated_at_utc: datetime = params[3]
    limit = params[6]
    rows = [
        row
        for row in connection.rows["idea_outbox_event"]
        if _delivery_ready(row, max_retry_count=max_retry_count, claimed_at_utc=evaluated_at_utc)
    ]
    rows.sort(key=lambda row: (row["occurred_at_utc"], row["outbox_event_id"]))
    return [dict(row) for row in rows[:limit]]


def outbox_readiness_summary_row(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    evaluated_at_utc: datetime = params[6]
    max_retry_count = params[9]
    rows = connection.rows["idea_outbox_event"]
    ready_rows = [
        row
        for row in rows
        if _delivery_ready(
            row,
            max_retry_count=max_retry_count,
            claimed_at_utc=evaluated_at_utc,
        )
    ]
    return [
        {
            "pending_count": _count_status(rows, OutboxEventStatus.PENDING),
            "leased_count": _count_status(rows, OutboxEventStatus.LEASED),
            "failed_count": _count_status(rows, OutboxEventStatus.FAILED),
            "published_count": _count_status(rows, OutboxEventStatus.PUBLISHED),
            "dead_letter_count": _count_status(rows, OutboxEventStatus.DEAD_LETTER),
            "expired_lease_count": sum(
                1
                for row in rows
                if row["status"] == OutboxEventStatus.LEASED.value
                and row["lease_expires_at_utc"] is not None
                and row["lease_expires_at_utc"] <= evaluated_at_utc
            ),
            "delivery_ready_count": sum(
                1
                for row in rows
                if _delivery_ready(
                    row,
                    max_retry_count=max_retry_count,
                    claimed_at_utc=evaluated_at_utc,
                )
            ),
            "retry_deferred_count": sum(
                1
                for row in rows
                if row["status"] == OutboxEventStatus.FAILED.value
                and row["retry_count"] < max_retry_count
                and row.get("next_attempt_at_utc") is not None
                and row["next_attempt_at_utc"] > evaluated_at_utc
            ),
            "oldest_delivery_ready_at_utc": min(
                (_delivery_ready_at_utc(row) for row in ready_rows),
                default=None,
            ),
        }
    ]


def _delivery_ready_at_utc(row: dict[str, Any]) -> datetime:
    if row["status"] == OutboxEventStatus.FAILED.value:
        return row["next_attempt_at_utc"]
    if row["status"] == OutboxEventStatus.LEASED.value:
        return row["lease_expires_at_utc"]
    return row["occurred_at_utc"]


def publish_outbox_event_row(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    status, published_at_utc, event_id, leased_status, lease_owner, lease_attempt_id = params
    for row in _matching_leased_rows(
        connection, event_id, leased_status, lease_owner, lease_attempt_id
    ):
        row["status"] = status
        row["published_at_utc"] = published_at_utc
        row["next_attempt_at_utc"] = None
        _clear_lease(row)
        return [dict(row)]
    return []


def fail_outbox_event_row(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    max_retry_count, dead_status, failed_status, failure_reason = params[:4]
    failed_at_utc = params[4]
    next_attempt_at_utc = params[7]
    event_id = params[8]
    leased_status = params[9]
    lease_owner = params[10]
    lease_attempt_id = params[11]
    for row in _matching_leased_rows(
        connection, event_id, leased_status, lease_owner, lease_attempt_id
    ):
        row["retry_count"] += 1
        row["status"] = dead_status if row["retry_count"] >= max_retry_count else failed_status
        row["published_at_utc"] = None
        row["failure_reason"] = failure_reason
        row["first_failed_at_utc"] = row.get("first_failed_at_utc") or failed_at_utc
        row["last_failed_at_utc"] = failed_at_utc
        row["next_attempt_at_utc"] = (
            None if row["retry_count"] >= max_retry_count else next_attempt_at_utc
        )
        _clear_lease(row)
        return [dict(row)]
    return []


def recover_dead_letter_row(
    connection: FakeOutboxConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    status, lease_owner, lease_attempt_id, lease_expires_at_utc, event_id, dead_status = params
    for row in connection.rows["idea_outbox_event"]:
        if row["outbox_event_id"] == event_id and row["status"] == dead_status:
            row["status"] = status
            row["published_at_utc"] = None
            row["next_attempt_at_utc"] = None
            row["lease_owner"] = lease_owner
            row["lease_attempt_id"] = lease_attempt_id
            row["lease_expires_at_utc"] = lease_expires_at_utc
            return [dict(row)]
    return []


def _delivery_ready(row: dict[str, Any], *, max_retry_count: int, claimed_at_utc: datetime) -> bool:
    return (
        row["status"] == OutboxEventStatus.PENDING.value
        or (
            row["status"] == OutboxEventStatus.FAILED.value
            and row["retry_count"] < max_retry_count
            and row.get("next_attempt_at_utc") is not None
            and row["next_attempt_at_utc"] <= claimed_at_utc
        )
        or (
            row["status"] == OutboxEventStatus.LEASED.value
            and row["lease_expires_at_utc"] is not None
            and row["lease_expires_at_utc"] <= claimed_at_utc
        )
    )


def _count_status(rows: Sequence[dict[str, Any]], status: OutboxEventStatus) -> int:
    return sum(1 for row in rows if row["status"] == status.value)


def _matching_leased_rows(
    connection: FakeOutboxConnection,
    event_id: str,
    leased_status: str,
    lease_owner: str,
    lease_attempt_id: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in connection.rows["idea_outbox_event"]
        if row["outbox_event_id"] == event_id
        and row["status"] == leased_status
        and row["lease_owner"] == lease_owner
        and row["lease_attempt_id"] == lease_attempt_id
    ]


def _clear_lease(row: dict[str, Any]) -> None:
    row["lease_owner"] = None
    row["lease_attempt_id"] = None
    row["lease_expires_at_utc"] = None
