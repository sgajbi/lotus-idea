from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping

from app.domain.events import (
    OutboxEventRecord,
    OutboxEventStatus,
    lease_outbox_event,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)


class OutboxDeliveryDecision(StrEnum):
    ACCEPTED = "accepted"
    NOT_FOUND = "not_found"
    ALREADY_PUBLISHED = "already_published"
    DEAD_LETTERED = "dead_lettered"
    LEASE_LOST = "lease_lost"


@dataclass(frozen=True)
class OutboxDeliveryResult:
    decision: OutboxDeliveryDecision
    event: OutboxEventRecord | None


def outbox_events_for_delivery(
    events: Mapping[str, OutboxEventRecord],
    *,
    limit: int,
    max_retry_count: int,
    evaluated_at_utc: datetime | None,
) -> tuple[OutboxEventRecord, ...]:
    _require_positive(limit, "limit")
    _require_positive(max_retry_count, "max_retry_count")
    evaluated_at = evaluated_at_utc or datetime.now(UTC)
    _require_aware_utc(evaluated_at, "evaluated_at_utc")
    delivery_ready = [
        event
        for event in events.values()
        if _outbox_event_delivery_ready(
            event,
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at,
        )
    ]
    return tuple(
        sorted(delivery_ready, key=lambda event: (event.occurred_at_utc, event.event_id))[:limit]
    )


def claim_outbox_events_for_delivery(
    events: dict[str, OutboxEventRecord],
    *,
    limit: int,
    max_retry_count: int,
    lease_owner: str,
    lease_attempt_id: str,
    claimed_at_utc: datetime,
    lease_expires_at_utc: datetime,
) -> tuple[OutboxEventRecord, ...]:
    _require_positive(limit, "limit")
    _require_positive(max_retry_count, "max_retry_count")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    _require_aware_utc(claimed_at_utc, "claimed_at_utc")
    _require_aware_utc(lease_expires_at_utc, "lease_expires_at_utc")
    if lease_expires_at_utc <= claimed_at_utc:
        raise ValueError("lease_expires_at_utc must be after claimed_at_utc")

    claimed: list[OutboxEventRecord] = []
    for event in outbox_events_for_delivery(
        events,
        limit=limit,
        max_retry_count=max_retry_count,
        evaluated_at_utc=claimed_at_utc,
    ):
        leased = lease_outbox_event(
            event,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            lease_expires_at_utc=lease_expires_at_utc,
        )
        events[event.event_id] = leased
        claimed.append(leased)
    return tuple(claimed)


def mark_owned_outbox_event_published(
    events: dict[str, OutboxEventRecord],
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
    event = events.get(event_id)
    terminal = _terminal_outbox_delivery_result(event)
    if terminal is not None:
        return terminal
    assert event is not None
    if not _event_owned_by_delivery_attempt(
        event,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
    ):
        return OutboxDeliveryResult(decision=OutboxDeliveryDecision.LEASE_LOST, event=event)
    updated = mark_outbox_event_published(event, published_at_utc=published_at_utc)
    events[event_id] = updated
    return OutboxDeliveryResult(decision=OutboxDeliveryDecision.ACCEPTED, event=updated)


def mark_owned_outbox_event_failed(
    events: dict[str, OutboxEventRecord],
    event_id: str,
    *,
    lease_owner: str,
    lease_attempt_id: str,
    failure_reason: str,
    max_retry_count: int,
) -> OutboxDeliveryResult:
    _require_text(event_id, "event_id")
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    event = events.get(event_id)
    terminal = _terminal_outbox_delivery_result(event)
    if terminal is not None:
        return terminal
    assert event is not None
    if not _event_owned_by_delivery_attempt(
        event,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
    ):
        return OutboxDeliveryResult(decision=OutboxDeliveryDecision.LEASE_LOST, event=event)
    updated = mark_outbox_event_failed(
        event,
        failure_reason=failure_reason,
        max_retry_count=max_retry_count,
    )
    events[event_id] = updated
    decision = (
        OutboxDeliveryDecision.DEAD_LETTERED
        if updated.status is OutboxEventStatus.DEAD_LETTER
        else OutboxDeliveryDecision.ACCEPTED
    )
    return OutboxDeliveryResult(decision=decision, event=updated)


def _terminal_outbox_delivery_result(
    event: OutboxEventRecord | None,
) -> OutboxDeliveryResult | None:
    if event is None:
        return OutboxDeliveryResult(decision=OutboxDeliveryDecision.NOT_FOUND, event=None)
    if event.status is OutboxEventStatus.PUBLISHED:
        return OutboxDeliveryResult(
            decision=OutboxDeliveryDecision.ALREADY_PUBLISHED,
            event=event,
        )
    if event.status is OutboxEventStatus.DEAD_LETTER:
        return OutboxDeliveryResult(decision=OutboxDeliveryDecision.DEAD_LETTERED, event=event)
    return None


def _outbox_event_delivery_ready(
    event: OutboxEventRecord,
    *,
    max_retry_count: int,
    evaluated_at_utc: datetime,
) -> bool:
    return (
        event.status is OutboxEventStatus.PENDING
        or (event.status is OutboxEventStatus.FAILED and event.retry_count < max_retry_count)
        or (
            event.status is OutboxEventStatus.LEASED
            and event.lease_expires_at_utc is not None
            and event.lease_expires_at_utc <= evaluated_at_utc
        )
    )


def _event_owned_by_delivery_attempt(
    event: OutboxEventRecord,
    *,
    lease_owner: str,
    lease_attempt_id: str,
) -> bool:
    return (
        event.status is OutboxEventStatus.LEASED
        and event.lease_owner == lease_owner
        and event.lease_attempt_id == lease_attempt_id
    )


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
