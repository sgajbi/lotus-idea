from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, Sequence

from app.domain.events import (
    OutboxEventRecord,
    OutboxEventStatus,
    validate_outbox_failure_reason,
)
from app.domain.outbox_delivery_state import OutboxDeliveryDecision, OutboxDeliveryResult
from app.infrastructure.postgres_codecs import read_json_object, read_row_value


class PostgresCursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...

    def fetchall(self) -> Sequence[Any]: ...

    def __enter__(self) -> PostgresCursor: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class PostgresConnection(Protocol):
    def cursor(self) -> PostgresCursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


OUTBOX_EVENT_RETURNING_COLUMNS = """
outbox_event_id, event_type, aggregate_type, aggregate_id, schema_version,
payload_json, status, occurred_at_utc, idempotency_fingerprint, correlation_id,
causation_id, published_at_utc, failure_reason, retry_count, lease_owner,
lease_attempt_id, lease_expires_at_utc
"""


def claim_outbox_events_for_delivery(
    connection: PostgresConnection,
    *,
    limit: int,
    max_retry_count: int,
    lease_owner: str,
    lease_attempt_id: str,
    claimed_at_utc: datetime,
    lease_expires_at_utc: datetime,
) -> tuple[OutboxEventRecord, ...]:
    _validate_claim(
        limit, max_retry_count, lease_owner, lease_attempt_id, claimed_at_utc, lease_expires_at_utc
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH selected AS (
                    SELECT outbox_event_id
                    FROM idea_outbox_event
                    WHERE status = %s
                       OR (status = %s AND retry_count < %s)
                       OR (status = %s AND lease_expires_at_utc <= %s)
                    ORDER BY occurred_at_utc, outbox_event_id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE idea_outbox_event AS event
                SET status = %s,
                    failure_reason = NULL,
                    lease_owner = %s,
                    lease_attempt_id = %s,
                    lease_expires_at_utc = %s
                FROM selected
                WHERE event.outbox_event_id = selected.outbox_event_id
                RETURNING {OUTBOX_EVENT_RETURNING_COLUMNS}
                """,
                (
                    OutboxEventStatus.PENDING.value,
                    OutboxEventStatus.FAILED.value,
                    max_retry_count,
                    OutboxEventStatus.LEASED.value,
                    claimed_at_utc,
                    limit,
                    OutboxEventStatus.LEASED.value,
                    lease_owner,
                    lease_attempt_id,
                    lease_expires_at_utc,
                ),
            )
            events = tuple(outbox_event_from_row(row) for row in cursor.fetchall())
        connection.commit()
        return events
    except Exception:
        connection.rollback()
        raise


def mark_outbox_event_published(
    connection: PostgresConnection,
    event_id: str,
    *,
    lease_owner: str,
    lease_attempt_id: str,
    published_at_utc: datetime,
) -> OutboxDeliveryResult:
    _require_text(event_id, "event_id")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    _require_aware_utc(published_at_utc, "published_at_utc")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE idea_outbox_event
                SET status = %s,
                    published_at_utc = %s,
                    failure_reason = NULL,
                    lease_owner = NULL,
                    lease_attempt_id = NULL,
                    lease_expires_at_utc = NULL
                WHERE outbox_event_id = %s
                  AND status = %s
                  AND lease_owner = %s
                  AND lease_attempt_id = %s
                RETURNING {OUTBOX_EVENT_RETURNING_COLUMNS}
                """,
                (
                    OutboxEventStatus.PUBLISHED.value,
                    published_at_utc,
                    event_id,
                    OutboxEventStatus.LEASED.value,
                    lease_owner,
                    lease_attempt_id,
                ),
            )
            rows = cursor.fetchall()
            result = (
                OutboxDeliveryResult(
                    decision=OutboxDeliveryDecision.ACCEPTED,
                    event=outbox_event_from_row(rows[0]),
                )
                if rows
                else _unowned_outbox_delivery_result(cursor, event_id)
            )
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise


def mark_outbox_event_failed(
    connection: PostgresConnection,
    event_id: str,
    *,
    lease_owner: str,
    lease_attempt_id: str,
    failure_reason: str,
    max_retry_count: int,
) -> OutboxDeliveryResult:
    _validate_failure(event_id, lease_owner, lease_attempt_id, failure_reason, max_retry_count)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE idea_outbox_event
                SET retry_count = retry_count + 1,
                    status = CASE WHEN retry_count + 1 >= %s THEN %s ELSE %s END,
                    published_at_utc = NULL,
                    failure_reason = %s,
                    lease_owner = NULL,
                    lease_attempt_id = NULL,
                    lease_expires_at_utc = NULL
                WHERE outbox_event_id = %s
                  AND status = %s
                  AND lease_owner = %s
                  AND lease_attempt_id = %s
                RETURNING {OUTBOX_EVENT_RETURNING_COLUMNS}
                """,
                (
                    max_retry_count,
                    OutboxEventStatus.DEAD_LETTER.value,
                    OutboxEventStatus.FAILED.value,
                    failure_reason,
                    event_id,
                    OutboxEventStatus.LEASED.value,
                    lease_owner,
                    lease_attempt_id,
                ),
            )
            rows = cursor.fetchall()
            result = _failed_delivery_result(rows, cursor, event_id)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise


def outbox_event_from_row(row: Any) -> OutboxEventRecord:
    return OutboxEventRecord(
        event_id=read_row_value(row, "outbox_event_id"),
        event_type=read_row_value(row, "event_type"),
        aggregate_type=read_row_value(row, "aggregate_type"),
        aggregate_id=read_row_value(row, "aggregate_id"),
        schema_version=read_row_value(row, "schema_version"),
        payload=read_json_object(row, "payload_json"),
        status=OutboxEventStatus(read_row_value(row, "status")),
        occurred_at_utc=read_row_value(row, "occurred_at_utc"),
        idempotency_fingerprint=read_row_value(row, "idempotency_fingerprint"),
        correlation_id=read_row_value(row, "correlation_id"),
        causation_id=read_row_value(row, "causation_id"),
        published_at_utc=read_row_value(row, "published_at_utc"),
        failure_reason=read_row_value(row, "failure_reason"),
        retry_count=read_row_value(row, "retry_count"),
        lease_owner=read_row_value(row, "lease_owner"),
        lease_attempt_id=read_row_value(row, "lease_attempt_id"),
        lease_expires_at_utc=read_row_value(row, "lease_expires_at_utc"),
    )


def _failed_delivery_result(
    rows: Sequence[Any],
    cursor: PostgresCursor,
    event_id: str,
) -> OutboxDeliveryResult:
    if not rows:
        return _unowned_outbox_delivery_result(cursor, event_id)
    event = outbox_event_from_row(rows[0])
    decision = (
        OutboxDeliveryDecision.DEAD_LETTERED
        if event.status is OutboxEventStatus.DEAD_LETTER
        else OutboxDeliveryDecision.ACCEPTED
    )
    return OutboxDeliveryResult(decision=decision, event=event)


def _unowned_outbox_delivery_result(cursor: PostgresCursor, event_id: str) -> OutboxDeliveryResult:
    cursor.execute(
        f"""
        SELECT {OUTBOX_EVENT_RETURNING_COLUMNS}
        FROM idea_outbox_event
        WHERE outbox_event_id = %s
        """,
        (event_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return OutboxDeliveryResult(decision=OutboxDeliveryDecision.NOT_FOUND, event=None)
    event = outbox_event_from_row(rows[0])
    if event.status is OutboxEventStatus.PUBLISHED:
        decision = OutboxDeliveryDecision.ALREADY_PUBLISHED
    elif event.status is OutboxEventStatus.DEAD_LETTER:
        decision = OutboxDeliveryDecision.DEAD_LETTERED
    else:
        decision = OutboxDeliveryDecision.LEASE_LOST
    return OutboxDeliveryResult(decision=decision, event=event)


def _validate_claim(
    limit: int,
    max_retry_count: int,
    lease_owner: str,
    lease_attempt_id: str,
    claimed_at_utc: datetime,
    lease_expires_at_utc: datetime,
) -> None:
    _require_positive(limit, "limit")
    _require_positive(max_retry_count, "max_retry_count")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    _require_aware_utc(claimed_at_utc, "claimed_at_utc")
    _require_aware_utc(lease_expires_at_utc, "lease_expires_at_utc")
    if lease_expires_at_utc <= claimed_at_utc:
        raise ValueError("lease_expires_at_utc must be after claimed_at_utc")


def _validate_failure(
    event_id: str,
    lease_owner: str,
    lease_attempt_id: str,
    failure_reason: str,
    max_retry_count: int,
) -> None:
    _require_text(event_id, "event_id")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    validate_outbox_failure_reason(failure_reason)
    _require_positive(max_retry_count, "max_retry_count")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
