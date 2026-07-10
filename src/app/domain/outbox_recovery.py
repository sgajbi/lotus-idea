from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
from typing import Any, Mapping

from app.domain.events import (
    OUTBOX_EVENT_SCHEMA_VERSION,
    SUPPORTED_OUTBOX_EVENT_TYPES,
    OutboxEventRecord,
    OutboxEventStatus,
    lease_outbox_event,
)
from app.domain.idempotency import payload_fingerprint


OUTBOX_DEAD_LETTER_SUPPORT_PREFIX = "outbox-dlq-"
OUTBOX_RECOVERY_OWNER = "lotus-idea-operations"
MAX_OUTBOX_RECOVERY_ATTEMPTS = 1


class OutboxRecoveryDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    NOT_DEAD_LETTERED = "not_dead_lettered"
    INELIGIBLE = "ineligible"
    RECOVERY_LIMIT_REACHED = "recovery_limit_reached"
    LEASE_CONFLICT = "lease_conflict"


@dataclass(frozen=True)
class OutboxDeadLetterSummary:
    support_reference: str
    event_family: str
    schema_version: str
    retry_count: int
    first_failed_at_utc: datetime
    last_failed_at_utc: datetime
    failure_reason: str
    recovery_eligible: bool
    recovery_blocker: str | None
    disposition: str = "quarantined"
    owner: str = OUTBOX_RECOVERY_OWNER


@dataclass(frozen=True)
class OutboxRecoveryAuditRecord:
    recovery_id: str
    event_id: str
    support_reference: str
    idempotency_fingerprint: str
    request_fingerprint: str
    actor_subject: str
    reason: str
    change_reference: str
    requested_at_utc: datetime
    lease_owner: str
    lease_attempt_id: str
    lease_expires_at_utc: datetime
    original_retry_count: int
    original_failure_reason: str
    original_first_failed_at_utc: datetime
    original_last_failed_at_utc: datetime


@dataclass(frozen=True)
class OutboxRecoveryClaimResult:
    decision: OutboxRecoveryDecision
    event: OutboxEventRecord | None
    audit_record: OutboxRecoveryAuditRecord | None
    blocker: str | None = None


def dead_letter_summary(event: OutboxEventRecord) -> OutboxDeadLetterSummary:
    if event.status is not OutboxEventStatus.DEAD_LETTER:
        raise ValueError("dead-letter summary requires a dead-lettered event")
    assert event.first_failed_at_utc is not None
    assert event.last_failed_at_utc is not None
    assert event.failure_reason is not None
    blocker = outbox_recovery_eligibility_blocker(
        event_type=event.event_type,
        schema_version=event.schema_version,
    )
    return OutboxDeadLetterSummary(
        support_reference=outbox_dead_letter_support_reference(event.event_id),
        event_family=event.event_type,
        schema_version=event.schema_version,
        retry_count=event.retry_count,
        first_failed_at_utc=event.first_failed_at_utc,
        last_failed_at_utc=event.last_failed_at_utc,
        failure_reason=event.failure_reason,
        recovery_eligible=blocker is None,
        recovery_blocker=blocker,
    )


def outbox_dead_letter_support_reference(event_id: str) -> str:
    _require_text(event_id, "event_id")
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:24]
    return f"{OUTBOX_DEAD_LETTER_SUPPORT_PREFIX}{digest}"


def outbox_recovery_eligibility_blocker(*, event_type: str, schema_version: str) -> str | None:
    if event_type not in SUPPORTED_OUTBOX_EVENT_TYPES:
        return "unsupported_event_family"
    if schema_version != OUTBOX_EVENT_SCHEMA_VERSION:
        return "unsupported_schema_version"
    return None


def outbox_recovery_request_payload(
    *,
    support_reference: str,
    reason: str,
    change_reference: str,
    actor_subject: str,
) -> dict[str, str]:
    for field_name, value in (
        ("support_reference", support_reference),
        ("reason", reason),
        ("change_reference", change_reference),
        ("actor_subject", actor_subject),
    ):
        _require_text(value, field_name)
    return {
        "supportReference": support_reference,
        "reason": reason,
        "changeReference": change_reference,
        "actorSubject": actor_subject,
    }


def build_outbox_recovery_audit_record(
    event: OutboxEventRecord,
    *,
    idempotency_key: str,
    request_payload: Mapping[str, Any],
    actor_subject: str,
    reason: str,
    change_reference: str,
    requested_at_utc: datetime,
    lease_owner: str,
    lease_attempt_id: str,
    lease_expires_at_utc: datetime,
) -> OutboxRecoveryAuditRecord:
    if event.status is not OutboxEventStatus.DEAD_LETTER:
        raise ValueError("outbox recovery requires a dead-lettered event")
    for field_name, value in (
        ("idempotency_key", idempotency_key),
        ("actor_subject", actor_subject),
        ("reason", reason),
        ("change_reference", change_reference),
        ("lease_owner", lease_owner),
        ("lease_attempt_id", lease_attempt_id),
    ):
        _require_text(value, field_name)
    _require_aware_utc(requested_at_utc, "requested_at_utc")
    _require_aware_utc(lease_expires_at_utc, "lease_expires_at_utc")
    if lease_expires_at_utc <= requested_at_utc:
        raise ValueError("lease_expires_at_utc must be after requested_at_utc")
    assert event.failure_reason is not None
    assert event.first_failed_at_utc is not None
    assert event.last_failed_at_utc is not None
    idempotency_fingerprint = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    request_fingerprint = payload_fingerprint(dict(request_payload))
    recovery_id = hashlib.sha256(
        f"{event.event_id}:{idempotency_fingerprint}".encode("utf-8")
    ).hexdigest()
    return OutboxRecoveryAuditRecord(
        recovery_id=f"recovery_{recovery_id[:32]}",
        event_id=event.event_id,
        support_reference=outbox_dead_letter_support_reference(event.event_id),
        idempotency_fingerprint=idempotency_fingerprint,
        request_fingerprint=request_fingerprint,
        actor_subject=actor_subject,
        reason=reason,
        change_reference=change_reference,
        requested_at_utc=requested_at_utc,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=lease_expires_at_utc,
        original_retry_count=event.retry_count,
        original_failure_reason=event.failure_reason,
        original_first_failed_at_utc=event.first_failed_at_utc,
        original_last_failed_at_utc=event.last_failed_at_utc,
    )


def dead_letter_summaries(
    events: Mapping[str, OutboxEventRecord],
    *,
    limit: int,
) -> tuple[OutboxDeadLetterSummary, ...]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    dead_letters = sorted(
        (
            event
            for event in events.values()
            if event.status is OutboxEventStatus.DEAD_LETTER
        ),
        key=lambda event: (event.last_failed_at_utc or event.occurred_at_utc, event.event_id),
        reverse=True,
    )
    return tuple(dead_letter_summary(event) for event in dead_letters[:limit])


def claim_dead_letter_for_recovery(
    events: dict[str, OutboxEventRecord],
    recovery_records: dict[str, OutboxRecoveryAuditRecord],
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
    if max_recovery_attempts <= 0:
        raise ValueError("max_recovery_attempts must be positive")
    _require_text(support_reference, "support_reference")
    request_fingerprint = payload_fingerprint(dict(request_payload))
    idempotency_fingerprint = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    existing = next(
        (
            record
            for record in recovery_records.values()
            if record.idempotency_fingerprint == idempotency_fingerprint
        ),
        None,
    )
    if existing is not None:
        decision = (
            OutboxRecoveryDecision.REPLAYED
            if existing.request_fingerprint == request_fingerprint
            else OutboxRecoveryDecision.CONFLICT
        )
        return OutboxRecoveryClaimResult(
            decision=decision,
            event=events.get(existing.event_id),
            audit_record=existing,
            blocker="idempotency_conflict" if decision is OutboxRecoveryDecision.CONFLICT else None,
        )

    event = next(
        (
            candidate
            for candidate in events.values()
            if outbox_dead_letter_support_reference(candidate.event_id) == support_reference
        ),
        None,
    )
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
    eligibility_blocker = outbox_recovery_eligibility_blocker(
        event_type=event.event_type,
        schema_version=event.schema_version,
    )
    if eligibility_blocker is not None:
        return OutboxRecoveryClaimResult(
            decision=OutboxRecoveryDecision.INELIGIBLE,
            event=event,
            audit_record=None,
            blocker=eligibility_blocker,
        )
    recovery_count = sum(
        1 for record in recovery_records.values() if record.event_id == event.event_id
    )
    if recovery_count >= max_recovery_attempts:
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
    events[event.event_id] = leased
    recovery_records[audit_record.recovery_id] = audit_record
    return OutboxRecoveryClaimResult(
        decision=OutboxRecoveryDecision.ACCEPTED,
        event=leased,
        audit_record=audit_record,
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
