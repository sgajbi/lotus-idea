from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib
from typing import Any, Mapping

from app.application.outbox.delivery import publish_outbox_event_safely
from app.domain import OutboxDeliveryDecision, OutboxRecoveryDecision
from app.domain.outbox.recovery import outbox_recovery_request_payload
from app.ports.idea_repository import OutboxRecoveryRepository
from app.ports.outbox.publisher import OutboxEventPublisher


OUTBOX_RECOVERY_LEASE_OWNER = "lotus-idea-outbox-recovery"
OUTBOX_RECOVERY_LEASE_DURATION_SECONDS = 300


class OutboxRecoveryRunStatus(StrEnum):
    PUBLISHED = "published"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    QUARANTINED = "quarantined"
    DEAD_LETTERED = "dead_lettered"
    LEASE_LOST = "lease_lost"


@dataclass(frozen=True)
class OutboxRecoveryRunSummary:
    support_reference: str
    run_status: OutboxRecoveryRunStatus
    recovery_reference: str | None
    blocker: str | None
    publication_attempted: bool
    original_retry_count: int | None
    supportability_status: str = "not_certified"
    supported_feature_promoted: bool = False


def run_outbox_dead_letter_recovery(
    repository: OutboxRecoveryRepository,
    publisher: OutboxEventPublisher,
    *,
    support_reference: str,
    idempotency_key: str,
    reason: str,
    change_reference: str,
    actor_subject: str,
    requested_at_utc: datetime | None = None,
    lease_duration_seconds: int = OUTBOX_RECOVERY_LEASE_DURATION_SECONDS,
) -> OutboxRecoveryRunSummary:
    requested_at = requested_at_utc or datetime.now(UTC)
    _require_aware_utc(requested_at, "requested_at_utc")
    _require_positive(lease_duration_seconds, "lease_duration_seconds")
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason=reason,
        change_reference=change_reference,
        actor_subject=actor_subject,
    )
    attempt_id = outbox_recovery_attempt_id(idempotency_key)
    claim = repository.claim_dead_letter_for_recovery(
        support_reference=support_reference,
        idempotency_key=idempotency_key,
        request_payload=request_payload,
        actor_subject=actor_subject,
        reason=reason,
        change_reference=change_reference,
        requested_at_utc=requested_at,
        lease_owner=OUTBOX_RECOVERY_LEASE_OWNER,
        lease_attempt_id=attempt_id,
        lease_expires_at_utc=requested_at + timedelta(seconds=lease_duration_seconds),
    )
    no_publication = _no_publication_summary(support_reference, claim.decision, claim)
    if no_publication is not None:
        return no_publication
    assert claim.event is not None
    assert claim.audit_record is not None
    outcome = publish_outbox_event_safely(publisher, claim.event)
    if outcome.accepted:
        delivery = repository.mark_outbox_event_published(
            claim.event.event_id,
            lease_owner=OUTBOX_RECOVERY_LEASE_OWNER,
            lease_attempt_id=attempt_id,
            published_at_utc=requested_at,
        )
    else:
        delivery = repository.mark_outbox_event_failed(
            claim.event.event_id,
            lease_owner=OUTBOX_RECOVERY_LEASE_OWNER,
            lease_attempt_id=attempt_id,
            failure_reason=outcome.failure_reason or "publisher_rejected",
            failed_at_utc=requested_at,
            max_retry_count=claim.event.retry_count + 1,
        )
    if delivery.decision is OutboxDeliveryDecision.ACCEPTED and outcome.accepted:
        status = OutboxRecoveryRunStatus.PUBLISHED
        blocker = None
    elif delivery.decision is OutboxDeliveryDecision.DEAD_LETTERED:
        status = OutboxRecoveryRunStatus.DEAD_LETTERED
        blocker = outcome.failure_reason or "publisher_rejected"
    else:
        status = OutboxRecoveryRunStatus.LEASE_LOST
        blocker = "recovery_lease_lost"
    return OutboxRecoveryRunSummary(
        support_reference=support_reference,
        run_status=status,
        recovery_reference=claim.audit_record.recovery_id,
        blocker=blocker,
        publication_attempted=True,
        original_retry_count=claim.audit_record.original_retry_count,
    )


def outbox_recovery_attempt_id(idempotency_key: str) -> str:
    if not idempotency_key.strip():
        raise ValueError("idempotency_key is required")
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"outbox-recovery-{digest}"


def outbox_recovery_api_request_payload(
    *,
    support_reference: str,
    reason: str,
    change_reference: str,
    actor_subject: str,
) -> Mapping[str, Any]:
    return outbox_recovery_request_payload(
        support_reference=support_reference,
        reason=reason,
        change_reference=change_reference,
        actor_subject=actor_subject,
    )


def _no_publication_summary(
    support_reference: str,
    decision: OutboxRecoveryDecision,
    claim: Any,
) -> OutboxRecoveryRunSummary | None:
    status_by_decision = {
        OutboxRecoveryDecision.REPLAYED: OutboxRecoveryRunStatus.REPLAYED,
        OutboxRecoveryDecision.CONFLICT: OutboxRecoveryRunStatus.CONFLICT,
        OutboxRecoveryDecision.NOT_FOUND: OutboxRecoveryRunStatus.NOT_FOUND,
        OutboxRecoveryDecision.NOT_DEAD_LETTERED: OutboxRecoveryRunStatus.QUARANTINED,
        OutboxRecoveryDecision.INELIGIBLE: OutboxRecoveryRunStatus.QUARANTINED,
        OutboxRecoveryDecision.RECOVERY_LIMIT_REACHED: OutboxRecoveryRunStatus.QUARANTINED,
        OutboxRecoveryDecision.LEASE_CONFLICT: OutboxRecoveryRunStatus.LEASE_LOST,
    }
    status = status_by_decision.get(decision)
    if status is None:
        return None
    audit_record = claim.audit_record
    return OutboxRecoveryRunSummary(
        support_reference=support_reference,
        run_status=status,
        recovery_reference=audit_record.recovery_id if audit_record is not None else None,
        blocker=claim.blocker,
        publication_attempted=False,
        original_retry_count=(
            audit_record.original_retry_count if audit_record is not None else None
        ),
    )


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
