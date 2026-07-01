from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, Sequence

from app.domain.events import (
    OutboxEventRecord,
    OutboxEventStatus,
    validate_outbox_failure_reason,
)
from app.domain.outbox_delivery_state import OutboxDeliveryDecision, OutboxDeliveryResult
from app.infrastructure.postgres_codecs import read_json_object, read_row_value
from app.ports.idea_repository import OutboxDeliveryReadinessRepositorySummary


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
causation_id, published_at_utc, failure_reason, retry_count, first_failed_at_utc,
last_failed_at_utc, next_attempt_at_utc, lease_owner, lease_attempt_id,
lease_expires_at_utc
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
                       OR (
                           status = %s
                           AND retry_count < %s
                           AND next_attempt_at_utc IS NOT NULL
                           AND next_attempt_at_utc <= %s
                       )
                       OR (status = %s AND lease_expires_at_utc <= %s)
                    ORDER BY occurred_at_utc, outbox_event_id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE idea_outbox_event AS event
                SET status = %s,
                    failure_reason = NULL,
                    next_attempt_at_utc = NULL,
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
                    claimed_at_utc,
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


def load_outbox_events_for_delivery(
    connection: PostgresConnection,
    *,
    limit: int,
    max_retry_count: int = 3,
    evaluated_at_utc: datetime,
) -> tuple[OutboxEventRecord, ...]:
    _require_positive(limit, "limit")
    _require_positive(max_retry_count, "max_retry_count")
    _require_aware_utc(evaluated_at_utc, "evaluated_at_utc")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            /* lotus-idea outbox-delivery-ready-events */
            SELECT {OUTBOX_EVENT_RETURNING_COLUMNS}
            FROM idea_outbox_event
            WHERE status = %s
               OR (
                   status = %s
                   AND retry_count < %s
                   AND next_attempt_at_utc IS NOT NULL
                   AND next_attempt_at_utc <= %s
               )
               OR (status = %s AND lease_expires_at_utc <= %s)
            ORDER BY occurred_at_utc, outbox_event_id
            LIMIT %s
            """,
            (
                OutboxEventStatus.PENDING.value,
                OutboxEventStatus.FAILED.value,
                max_retry_count,
                evaluated_at_utc,
                OutboxEventStatus.LEASED.value,
                evaluated_at_utc,
                limit,
            ),
        )
        return tuple(outbox_event_from_row(row) for row in cursor.fetchall())


def load_outbox_delivery_readiness_summary(
    connection: PostgresConnection,
    *,
    max_retry_count: int,
    evaluated_at_utc: datetime,
) -> OutboxDeliveryReadinessRepositorySummary:
    _require_positive(max_retry_count, "max_retry_count")
    _require_aware_utc(evaluated_at_utc, "evaluated_at_utc")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea outbox-readiness-summary */
            SELECT
                COUNT(*) FILTER (WHERE status = %s) AS pending_count,
                COUNT(*) FILTER (WHERE status = %s) AS leased_count,
                COUNT(*) FILTER (WHERE status = %s) AS failed_count,
                COUNT(*) FILTER (WHERE status = %s) AS published_count,
                COUNT(*) FILTER (WHERE status = %s) AS dead_letter_count,
                COUNT(*) FILTER (
                    WHERE status = %s AND lease_expires_at_utc <= %s
                ) AS expired_lease_count,
                COUNT(*) FILTER (
                    WHERE status = %s
                       OR (
                           status = %s
                           AND retry_count < %s
                           AND next_attempt_at_utc IS NOT NULL
                           AND next_attempt_at_utc <= %s
                       )
                       OR (status = %s AND lease_expires_at_utc <= %s)
                ) AS delivery_ready_count,
                COUNT(*) FILTER (
                    WHERE status = %s
                       AND retry_count < %s
                       AND next_attempt_at_utc IS NOT NULL
                       AND next_attempt_at_utc > %s
                ) AS retry_deferred_count
            FROM idea_outbox_event
            """,
            (
                OutboxEventStatus.PENDING.value,
                OutboxEventStatus.LEASED.value,
                OutboxEventStatus.FAILED.value,
                OutboxEventStatus.PUBLISHED.value,
                OutboxEventStatus.DEAD_LETTER.value,
                OutboxEventStatus.LEASED.value,
                evaluated_at_utc,
                OutboxEventStatus.PENDING.value,
                OutboxEventStatus.FAILED.value,
                max_retry_count,
                evaluated_at_utc,
                OutboxEventStatus.LEASED.value,
                evaluated_at_utc,
                OutboxEventStatus.FAILED.value,
                max_retry_count,
                evaluated_at_utc,
            ),
        )
        rows = cursor.fetchall()
    if not rows:
        return OutboxDeliveryReadinessRepositorySummary(
            pending_count=0,
            leased_count=0,
            failed_count=0,
            published_count=0,
            dead_letter_count=0,
            expired_lease_count=0,
            delivery_ready_count=0,
            retry_deferred_count=0,
        )
    return _outbox_readiness_summary_from_row(rows[0])


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
                    first_failed_at_utc = NULL,
                    last_failed_at_utc = NULL,
                    next_attempt_at_utc = NULL,
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
    failed_at_utc: datetime | None = None,
    max_retry_count: int = 3,
    next_attempt_at_utc: datetime | None = None,
) -> OutboxDeliveryResult:
    failed_at = failed_at_utc or datetime.now(UTC)
    retry_at = next_attempt_at_utc or failed_at + timedelta(seconds=60)
    _validate_failure(
        event_id,
        lease_owner,
        lease_attempt_id,
        failure_reason,
        failed_at,
        max_retry_count,
        retry_at,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE idea_outbox_event
                SET retry_count = retry_count + 1,
                    status = CASE WHEN retry_count + 1 >= %s THEN %s ELSE %s END,
                    published_at_utc = NULL,
                    failure_reason = %s,
                    first_failed_at_utc = COALESCE(first_failed_at_utc, %s),
                    last_failed_at_utc = %s,
                    next_attempt_at_utc = CASE
                        WHEN retry_count + 1 >= %s THEN NULL
                        ELSE %s
                    END,
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
                    failed_at,
                    failed_at,
                    max_retry_count,
                    retry_at,
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
        first_failed_at_utc=read_row_value(row, "first_failed_at_utc"),
        last_failed_at_utc=read_row_value(row, "last_failed_at_utc"),
        next_attempt_at_utc=read_row_value(row, "next_attempt_at_utc"),
        lease_owner=read_row_value(row, "lease_owner"),
        lease_attempt_id=read_row_value(row, "lease_attempt_id"),
        lease_expires_at_utc=read_row_value(row, "lease_expires_at_utc"),
    )


def _outbox_readiness_summary_from_row(row: Any) -> OutboxDeliveryReadinessRepositorySummary:
    return OutboxDeliveryReadinessRepositorySummary(
        pending_count=read_row_value(row, "pending_count"),
        leased_count=read_row_value(row, "leased_count"),
        failed_count=read_row_value(row, "failed_count"),
        published_count=read_row_value(row, "published_count"),
        dead_letter_count=read_row_value(row, "dead_letter_count"),
        expired_lease_count=read_row_value(row, "expired_lease_count"),
        delivery_ready_count=read_row_value(row, "delivery_ready_count"),
        retry_deferred_count=read_row_value(row, "retry_deferred_count"),
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
    failed_at_utc: datetime,
    max_retry_count: int,
    next_attempt_at_utc: datetime | None,
) -> None:
    _require_text(event_id, "event_id")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    validate_outbox_failure_reason(failure_reason)
    _require_aware_utc(failed_at_utc, "failed_at_utc")
    _require_positive(max_retry_count, "max_retry_count")
    if next_attempt_at_utc is not None:
        _require_aware_utc(next_attempt_at_utc, "next_attempt_at_utc")
        if next_attempt_at_utc <= failed_at_utc:
            raise ValueError("next_attempt_at_utc must be after failed_at_utc")


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
