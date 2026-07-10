from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any, Mapping, Sequence

from app.domain.events import OutboxEventRecord, OutboxEventStatus, lease_outbox_event
from app.domain.idempotency import payload_fingerprint
from app.domain.outbox_recovery import (
    MAX_OUTBOX_RECOVERY_ATTEMPTS,
    OutboxDeadLetterSummary,
    OutboxRecoveryAuditRecord,
    OutboxRecoveryClaimResult,
    OutboxRecoveryDecision,
    build_outbox_recovery_audit_record,
    dead_letter_summary,
    outbox_dead_letter_support_reference,
    outbox_recovery_eligibility_blocker,
)
from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_outbox_delivery import (
    OUTBOX_EVENT_RETURNING_COLUMNS,
    PostgresConnection,
    outbox_event_from_row,
)


MAX_DEAD_LETTER_RECOVERY_LOOKUP_ROWS = 1000
OUTBOX_RECOVERY_RETURNING_COLUMNS = """
recovery_id, outbox_event_id, support_reference, idempotency_fingerprint,
request_fingerprint, actor_subject, recovery_reason, change_reference,
requested_at_utc, lease_owner, lease_attempt_id, lease_expires_at_utc,
original_retry_count, original_failure_reason, original_first_failed_at_utc,
original_last_failed_at_utc
"""


def load_dead_letter_summaries(
    connection: PostgresConnection,
    *,
    limit: int,
) -> tuple[OutboxDeadLetterSummary, ...]:
    _require_positive(limit, "limit")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            /* lotus-idea outbox-dead-letter-summaries */
            SELECT {OUTBOX_EVENT_RETURNING_COLUMNS}
            FROM idea_outbox_event
            WHERE status = %s
            ORDER BY last_failed_at_utc DESC, outbox_event_id DESC
            LIMIT %s
            """,
            (OutboxEventStatus.DEAD_LETTER.value, limit),
        )
        return tuple(dead_letter_summary(outbox_event_from_row(row)) for row in cursor.fetchall())


def load_outbox_recovery_audit_records(
    connection: PostgresConnection,
) -> tuple[OutboxRecoveryAuditRecord, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            /* lotus-idea outbox-recovery-audit-records */
            SELECT {OUTBOX_RECOVERY_RETURNING_COLUMNS}
            FROM idea_outbox_recovery_audit
            ORDER BY requested_at_utc, recovery_id
            """
        )
        return tuple(_recovery_record_from_row(row) for row in cursor.fetchall())


def claim_dead_letter_for_recovery(
    connection: PostgresConnection,
    *,
    support_reference: str,
    idempotency_key: str,
    request_payload: Mapping[str, Any],
    actor_subject: str,
    reason: str,
    change_reference: str,
    requested_at_utc: datetime,
    lease_owner: str,
    lease_attempt_id: str,
    lease_expires_at_utc: datetime,
    max_recovery_attempts: int = MAX_OUTBOX_RECOVERY_ATTEMPTS,
) -> OutboxRecoveryClaimResult:
    _require_positive(max_recovery_attempts, "max_recovery_attempts")
    idempotency_fingerprint = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    request_fingerprint = payload_fingerprint(dict(request_payload))
    try:
        with connection.cursor() as cursor:
            existing = _load_recovery_by_idempotency(cursor, idempotency_fingerprint)
            if existing is not None:
                event = _load_event(cursor, existing.event_id)
                decision = (
                    OutboxRecoveryDecision.REPLAYED
                    if existing.request_fingerprint == request_fingerprint
                    else OutboxRecoveryDecision.CONFLICT
                )
                connection.commit()
                return OutboxRecoveryClaimResult(
                    decision=decision,
                    event=event,
                    audit_record=existing,
                    blocker=(
                        "idempotency_conflict"
                        if decision is OutboxRecoveryDecision.CONFLICT
                        else None
                    ),
                )

            event = _load_event_for_support_reference(cursor, support_reference)
            terminal = _terminal_recovery_result(event)
            if terminal is not None:
                connection.commit()
                return terminal
            assert event is not None
            eligibility_blocker = outbox_recovery_eligibility_blocker(
                event_type=event.event_type,
                schema_version=event.schema_version,
            )
            if eligibility_blocker is not None:
                connection.commit()
                return OutboxRecoveryClaimResult(
                    decision=OutboxRecoveryDecision.INELIGIBLE,
                    event=event,
                    audit_record=None,
                    blocker=eligibility_blocker,
                )
            recovery_count = _recovery_count(cursor, event.event_id)
            if recovery_count >= max_recovery_attempts:
                connection.commit()
                return OutboxRecoveryClaimResult(
                    decision=OutboxRecoveryDecision.RECOVERY_LIMIT_REACHED,
                    event=event,
                    audit_record=None,
                    blocker="recovery_attempt_limit_reached",
                )
            audit_record = build_outbox_recovery_audit_record(
                event,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                actor_subject=actor_subject,
                reason=reason,
                change_reference=change_reference,
                requested_at_utc=requested_at_utc,
                lease_owner=lease_owner,
                lease_attempt_id=lease_attempt_id,
                lease_expires_at_utc=lease_expires_at_utc,
            )
            leased = lease_outbox_event(
                event,
                lease_owner=lease_owner,
                lease_attempt_id=lease_attempt_id,
                lease_expires_at_utc=lease_expires_at_utc,
            )
            cursor.execute(
                f"""
                UPDATE idea_outbox_event
                SET status = %s,
                    published_at_utc = NULL,
                    next_attempt_at_utc = NULL,
                    lease_owner = %s,
                    lease_attempt_id = %s,
                    lease_expires_at_utc = %s
                WHERE outbox_event_id = %s AND status = %s
                RETURNING {OUTBOX_EVENT_RETURNING_COLUMNS}
                """,
                (
                    OutboxEventStatus.LEASED.value,
                    lease_owner,
                    lease_attempt_id,
                    lease_expires_at_utc,
                    event.event_id,
                    OutboxEventStatus.DEAD_LETTER.value,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                connection.commit()
                return OutboxRecoveryClaimResult(
                    decision=OutboxRecoveryDecision.LEASE_CONFLICT,
                    event=_load_event(cursor, event.event_id),
                    audit_record=None,
                    blocker="recovery_lease_conflict",
                )
            cursor.execute(
                """
                INSERT INTO idea_outbox_recovery_audit (
                    recovery_id, outbox_event_id, support_reference,
                    idempotency_fingerprint, request_fingerprint, actor_subject,
                    recovery_reason, change_reference, requested_at_utc, lease_owner,
                    lease_attempt_id, lease_expires_at_utc, original_retry_count,
                    original_failure_reason, original_first_failed_at_utc,
                    original_last_failed_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                _recovery_record_values(audit_record),
            )
        connection.commit()
        return OutboxRecoveryClaimResult(
            decision=OutboxRecoveryDecision.ACCEPTED,
            event=leased,
            audit_record=audit_record,
        )
    except Exception:
        connection.rollback()
        raise


def _load_recovery_by_idempotency(
    cursor: Any,
    idempotency_fingerprint: str,
) -> OutboxRecoveryAuditRecord | None:
    cursor.execute(
        f"""
        SELECT {OUTBOX_RECOVERY_RETURNING_COLUMNS}
        FROM idea_outbox_recovery_audit
        WHERE idempotency_fingerprint = %s
        """,
        (idempotency_fingerprint,),
    )
    rows = cursor.fetchall()
    return _recovery_record_from_row(rows[0]) if rows else None


def _load_event_for_support_reference(
    cursor: Any,
    support_reference: str,
) -> OutboxEventRecord | None:
    cursor.execute(
        f"""
        SELECT {OUTBOX_EVENT_RETURNING_COLUMNS}
        FROM idea_outbox_event
        ORDER BY occurred_at_utc DESC, outbox_event_id DESC
        LIMIT %s
        FOR UPDATE
        """,
        (MAX_DEAD_LETTER_RECOVERY_LOOKUP_ROWS,),
    )
    return next(
        (
            event
            for event in (outbox_event_from_row(row) for row in cursor.fetchall())
            if outbox_dead_letter_support_reference(event.event_id) == support_reference
        ),
        None,
    )


def _load_event(cursor: Any, event_id: str) -> OutboxEventRecord | None:
    cursor.execute(
        f"SELECT {OUTBOX_EVENT_RETURNING_COLUMNS} FROM idea_outbox_event WHERE outbox_event_id = %s",
        (event_id,),
    )
    rows = cursor.fetchall()
    return outbox_event_from_row(rows[0]) if rows else None


def _recovery_count(cursor: Any, event_id: str) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS recovery_count FROM idea_outbox_recovery_audit WHERE outbox_event_id = %s",
        (event_id,),
    )
    rows = cursor.fetchall()
    return int(read_row_value(rows[0], "recovery_count")) if rows else 0


def _terminal_recovery_result(event: Any) -> OutboxRecoveryClaimResult | None:
    if event is None:
        return OutboxRecoveryClaimResult(
            decision=OutboxRecoveryDecision.NOT_FOUND,
            event=None,
            audit_record=None,
            blocker="dead_letter_not_found",
        )
    if event.status is OutboxEventStatus.LEASED:
        return OutboxRecoveryClaimResult(
            decision=OutboxRecoveryDecision.LEASE_CONFLICT,
            event=event,
            audit_record=None,
            blocker="recovery_lease_conflict",
        )
    if event.status is not OutboxEventStatus.DEAD_LETTER:
        return OutboxRecoveryClaimResult(
            decision=OutboxRecoveryDecision.NOT_DEAD_LETTERED,
            event=event,
            audit_record=None,
            blocker="event_not_dead_lettered",
        )
    return None


def _recovery_record_from_row(row: Any) -> OutboxRecoveryAuditRecord:
    return OutboxRecoveryAuditRecord(
        recovery_id=read_row_value(row, "recovery_id"),
        event_id=read_row_value(row, "outbox_event_id"),
        support_reference=read_row_value(row, "support_reference"),
        idempotency_fingerprint=read_row_value(row, "idempotency_fingerprint"),
        request_fingerprint=read_row_value(row, "request_fingerprint"),
        actor_subject=read_row_value(row, "actor_subject"),
        reason=read_row_value(row, "recovery_reason"),
        change_reference=read_row_value(row, "change_reference"),
        requested_at_utc=read_row_value(row, "requested_at_utc"),
        lease_owner=read_row_value(row, "lease_owner"),
        lease_attempt_id=read_row_value(row, "lease_attempt_id"),
        lease_expires_at_utc=read_row_value(row, "lease_expires_at_utc"),
        original_retry_count=read_row_value(row, "original_retry_count"),
        original_failure_reason=read_row_value(row, "original_failure_reason"),
        original_first_failed_at_utc=read_row_value(row, "original_first_failed_at_utc"),
        original_last_failed_at_utc=read_row_value(row, "original_last_failed_at_utc"),
    )


def _recovery_record_values(record: OutboxRecoveryAuditRecord) -> Sequence[Any]:
    return (
        record.recovery_id,
        record.event_id,
        record.support_reference,
        record.idempotency_fingerprint,
        record.request_fingerprint,
        record.actor_subject,
        record.reason,
        record.change_reference,
        record.requested_at_utc,
        record.lease_owner,
        record.lease_attempt_id,
        record.lease_expires_at_utc,
        record.original_retry_count,
        record.original_failure_reason,
        record.original_first_failed_at_utc,
        record.original_last_failed_at_utc,
    )


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
