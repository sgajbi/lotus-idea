from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain import OutboxDeliveryDecision, OutboxEventRecord, OutboxEventStatus
from app.ports.idea_repository import OutboxDeliveryRepository
from app.ports.outbox_publisher import OutboxEventPublisher, OutboxPublishOutcome


@dataclass(frozen=True)
class OutboxDeliveryRunSummary:
    attempted_count: int
    published_count: int
    failed_count: int
    dead_lettered_count: int
    skipped_count: int
    max_retry_count: int
    lease_owner: str
    lease_attempt_id: str
    supportability_status: str = "foundation_only"
    external_broker_publication_supported: bool = False


def run_outbox_delivery_once(
    repository: OutboxDeliveryRepository,
    publisher: OutboxEventPublisher,
    *,
    limit: int = 100,
    max_retry_count: int = 3,
    lease_owner: str | None = None,
    lease_attempt_id: str | None = None,
    lease_duration_seconds: int = 300,
    delivered_at_utc: datetime | None = None,
) -> OutboxDeliveryRunSummary:
    _require_positive(limit, "limit")
    _require_positive(max_retry_count, "max_retry_count")
    _require_positive(lease_duration_seconds, "lease_duration_seconds")
    delivered_at = delivered_at_utc or datetime.now(UTC)
    _require_aware_utc(delivered_at, "delivered_at_utc")
    owner = lease_owner or "lotus-idea-outbox-delivery"
    attempt_id = lease_attempt_id or f"outbox-delivery-{uuid4().hex}"
    _require_text(owner, "lease_owner")
    _require_text(attempt_id, "lease_attempt_id")

    events = repository.claim_outbox_events_for_delivery(
        limit=limit,
        max_retry_count=max_retry_count,
        lease_owner=owner,
        lease_attempt_id=attempt_id,
        claimed_at_utc=delivered_at,
        lease_expires_at_utc=delivered_at + timedelta(seconds=lease_duration_seconds),
    )
    published = 0
    failed = 0
    dead_lettered = 0
    skipped = 0

    for event in events:
        if event.status is not OutboxEventStatus.LEASED:
            skipped += 1
            continue
        outcome = _publish_safely(publisher, event)
        if outcome.accepted:
            result = repository.mark_outbox_event_published(
                event.event_id,
                lease_owner=owner,
                lease_attempt_id=attempt_id,
                published_at_utc=delivered_at,
            )
        else:
            result = repository.mark_outbox_event_failed(
                event.event_id,
                lease_owner=owner,
                lease_attempt_id=attempt_id,
                failure_reason=outcome.failure_reason or "publisher_rejected",
                max_retry_count=max_retry_count,
            )

        if result.decision is OutboxDeliveryDecision.ACCEPTED:
            if outcome.accepted:
                published += 1
            else:
                failed += 1
        elif result.decision is OutboxDeliveryDecision.DEAD_LETTERED:
            dead_lettered += 1
        else:
            skipped += 1

    return OutboxDeliveryRunSummary(
        attempted_count=len(events),
        published_count=published,
        failed_count=failed,
        dead_lettered_count=dead_lettered,
        skipped_count=skipped,
        max_retry_count=max_retry_count,
        lease_owner=owner,
        lease_attempt_id=attempt_id,
    )


def _publish_safely(
    publisher: OutboxEventPublisher,
    event: OutboxEventRecord,
) -> OutboxPublishOutcome:
    try:
        return publisher.publish(event)
    except Exception:
        return OutboxPublishOutcome.rejected_by_publisher("publisher_unavailable")


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
