from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib
from typing import Any, Mapping

from app.domain import OutboxDeliveryDecision, OutboxEventRecord, OutboxEventStatus
from app.domain.idempotency import IdempotencyDecision
from app.domain.outbox.delivery import (
    OUTBOX_RETRY_BACKOFF_BASE_SECONDS,
    OUTBOX_RETRY_BACKOFF_MAX_SECONDS,
    next_outbox_retry_attempt_at_utc,
)
from app.ports.idea_repository import OutboxDeliveryRepository
from app.ports.outbox.publisher import OutboxEventPublisher, OutboxPublishOutcome

OUTBOX_DELIVERY_RUN_ONCE_BATCH_CEILING = 100


class OutboxDeliveryRunStatus(StrEnum):
    COMPLETED = "completed"
    REPLAYED = "replayed"
    CONFLICT = "conflict"


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
    operator_run_reference: str
    run_status: OutboxDeliveryRunStatus = OutboxDeliveryRunStatus.COMPLETED
    supportability_status: str = "foundation_only"
    external_broker_publication_supported: bool = False
    retry_backoff_base_seconds: int = OUTBOX_RETRY_BACKOFF_BASE_SECONDS
    retry_backoff_max_seconds: int = OUTBOX_RETRY_BACKOFF_MAX_SECONDS


@dataclass(frozen=True)
class _OutboxDeliveryRunContext:
    delivered_at_utc: datetime
    lease_expires_at_utc: datetime
    lease_owner: str
    lease_attempt_id: str
    operator_run_reference: str


@dataclass(frozen=True)
class _OutboxDeliveryEventResult:
    publisher_accepted: bool
    repository_decision: OutboxDeliveryDecision


@dataclass
class _OutboxDeliveryCounters:
    published_count: int = 0
    failed_count: int = 0
    dead_lettered_count: int = 0
    skipped_count: int = 0

    def record(self, result: _OutboxDeliveryEventResult) -> None:
        if result.repository_decision is OutboxDeliveryDecision.ACCEPTED:
            if result.publisher_accepted:
                self.published_count += 1
            else:
                self.failed_count += 1
        elif result.repository_decision is OutboxDeliveryDecision.DEAD_LETTERED:
            self.dead_lettered_count += 1
        else:
            self.skipped_count += 1


def outbox_delivery_run_request_payload(
    *,
    limit: int,
    max_retry_count: int,
    delivered_at_utc: datetime | None,
    caller_subject: str,
) -> dict[str, Any]:
    _require_delivery_limit(limit)
    _require_positive(max_retry_count, "max_retry_count")
    _require_text(caller_subject, "caller_subject")
    if delivered_at_utc is not None:
        _require_aware_utc(delivered_at_utc, "delivered_at_utc")
    return {
        "limit": limit,
        "max_retry_count": max_retry_count,
        "delivered_at_utc": delivered_at_utc.isoformat() if delivered_at_utc else None,
        "caller_subject": caller_subject,
    }


def operator_run_reference_for_idempotency_key(idempotency_key: str) -> str:
    _require_text(idempotency_key, "idempotency_key")
    digest = hashlib.sha256(idempotency_key.strip().encode("utf-8")).hexdigest()
    return f"outbox-run-{digest[:24]}"


def run_outbox_delivery_once(
    repository: OutboxDeliveryRepository,
    publisher: OutboxEventPublisher,
    *,
    limit: int = OUTBOX_DELIVERY_RUN_ONCE_BATCH_CEILING,
    max_retry_count: int = 3,
    idempotency_key: str,
    request_payload: Mapping[str, Any],
    lease_owner: str | None = None,
    lease_attempt_id: str | None = None,
    lease_duration_seconds: int = 300,
    delivered_at_utc: datetime | None = None,
) -> OutboxDeliveryRunSummary:
    _require_delivery_limit(limit)
    _require_positive(max_retry_count, "max_retry_count")
    _require_text(idempotency_key, "idempotency_key")
    context = _outbox_delivery_run_context(
        idempotency_key=idempotency_key,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_duration_seconds=lease_duration_seconds,
        delivered_at_utc=delivered_at_utc,
    )

    idempotency_status = _record_outbox_delivery_run_request(
        repository,
        idempotency_key=idempotency_key,
        request_payload=request_payload,
    )
    if idempotency_status is not None:
        return _outbox_delivery_no_mutation_summary(
            max_retry_count=max_retry_count,
            context=context,
            run_status=idempotency_status,
        )

    events = _claim_outbox_delivery_events(
        repository,
        limit=limit,
        max_retry_count=max_retry_count,
        context=context,
    )
    counters = _deliver_outbox_events(
        repository,
        publisher,
        events=events,
        max_retry_count=max_retry_count,
        context=context,
    )
    return _outbox_delivery_run_summary(
        attempted_count=len(events),
        counters=counters,
        max_retry_count=max_retry_count,
        context=context,
        run_status=OutboxDeliveryRunStatus.COMPLETED,
    )


def _outbox_delivery_run_context(
    *,
    idempotency_key: str,
    lease_owner: str | None,
    lease_attempt_id: str | None,
    lease_duration_seconds: int,
    delivered_at_utc: datetime | None,
) -> _OutboxDeliveryRunContext:
    _require_positive(lease_duration_seconds, "lease_duration_seconds")
    delivered_at = delivered_at_utc or datetime.now(UTC)
    _require_aware_utc(delivered_at, "delivered_at_utc")
    operator_run_reference = operator_run_reference_for_idempotency_key(idempotency_key)
    owner = lease_owner or "lotus-idea-outbox-delivery"
    attempt_id = lease_attempt_id or operator_run_reference
    _require_text(owner, "lease_owner")
    _require_text(attempt_id, "lease_attempt_id")
    return _OutboxDeliveryRunContext(
        delivered_at_utc=delivered_at,
        lease_expires_at_utc=delivered_at + timedelta(seconds=lease_duration_seconds),
        lease_owner=owner,
        lease_attempt_id=attempt_id,
        operator_run_reference=operator_run_reference,
    )


def _record_outbox_delivery_run_request(
    repository: OutboxDeliveryRepository,
    *,
    idempotency_key: str,
    request_payload: Mapping[str, Any],
) -> OutboxDeliveryRunStatus | None:
    idempotency_decision = repository.record_outbox_delivery_run_request(
        idempotency_key=idempotency_key,
        payload=dict(request_payload),
    )
    if idempotency_decision is IdempotencyDecision.CONFLICT:
        return OutboxDeliveryRunStatus.CONFLICT
    if idempotency_decision is IdempotencyDecision.REPLAYED:
        return OutboxDeliveryRunStatus.REPLAYED
    return None


def _claim_outbox_delivery_events(
    repository: OutboxDeliveryRepository,
    *,
    limit: int,
    max_retry_count: int,
    context: _OutboxDeliveryRunContext,
) -> tuple[OutboxEventRecord, ...]:
    return repository.claim_outbox_events_for_delivery(
        limit=limit,
        max_retry_count=max_retry_count,
        lease_owner=context.lease_owner,
        lease_attempt_id=context.lease_attempt_id,
        claimed_at_utc=context.delivered_at_utc,
        lease_expires_at_utc=context.lease_expires_at_utc,
    )


def _deliver_outbox_events(
    repository: OutboxDeliveryRepository,
    publisher: OutboxEventPublisher,
    *,
    events: tuple[OutboxEventRecord, ...],
    max_retry_count: int,
    context: _OutboxDeliveryRunContext,
) -> _OutboxDeliveryCounters:
    counters = _OutboxDeliveryCounters()
    for event in events:
        counters.record(
            _deliver_outbox_event(
                repository,
                publisher,
                event=event,
                max_retry_count=max_retry_count,
                context=context,
            )
        )
    return counters


def _deliver_outbox_event(
    repository: OutboxDeliveryRepository,
    publisher: OutboxEventPublisher,
    *,
    event: OutboxEventRecord,
    max_retry_count: int,
    context: _OutboxDeliveryRunContext,
) -> _OutboxDeliveryEventResult:
    if event.status is not OutboxEventStatus.LEASED:
        return _OutboxDeliveryEventResult(
            publisher_accepted=False,
            repository_decision=OutboxDeliveryDecision.LEASE_LOST,
        )

    outcome = publish_outbox_event_safely(publisher, event)
    if outcome.accepted:
        result = repository.mark_outbox_event_published(
            event.event_id,
            lease_owner=context.lease_owner,
            lease_attempt_id=context.lease_attempt_id,
            published_at_utc=context.delivered_at_utc,
        )
    else:
        result = repository.mark_outbox_event_failed(
            event.event_id,
            lease_owner=context.lease_owner,
            lease_attempt_id=context.lease_attempt_id,
            failure_reason=outcome.failure_reason or "publisher_rejected",
            failed_at_utc=context.delivered_at_utc,
            max_retry_count=max_retry_count,
            next_attempt_at_utc=next_outbox_retry_attempt_at_utc(
                event,
                failed_at_utc=context.delivered_at_utc,
                max_retry_count=max_retry_count,
            ),
        )
    return _OutboxDeliveryEventResult(
        publisher_accepted=outcome.accepted,
        repository_decision=result.decision,
    )


def _outbox_delivery_run_summary(
    *,
    attempted_count: int,
    counters: _OutboxDeliveryCounters,
    max_retry_count: int,
    context: _OutboxDeliveryRunContext,
    run_status: OutboxDeliveryRunStatus,
) -> OutboxDeliveryRunSummary:
    return OutboxDeliveryRunSummary(
        attempted_count=attempted_count,
        published_count=counters.published_count,
        failed_count=counters.failed_count,
        dead_lettered_count=counters.dead_lettered_count,
        skipped_count=counters.skipped_count,
        max_retry_count=max_retry_count,
        retry_backoff_base_seconds=OUTBOX_RETRY_BACKOFF_BASE_SECONDS,
        retry_backoff_max_seconds=OUTBOX_RETRY_BACKOFF_MAX_SECONDS,
        lease_owner=context.lease_owner,
        lease_attempt_id=context.lease_attempt_id,
        operator_run_reference=context.operator_run_reference,
        run_status=run_status,
    )


def _outbox_delivery_no_mutation_summary(
    *,
    max_retry_count: int,
    context: _OutboxDeliveryRunContext,
    run_status: OutboxDeliveryRunStatus,
) -> OutboxDeliveryRunSummary:
    return _outbox_delivery_run_summary(
        attempted_count=0,
        counters=_OutboxDeliveryCounters(),
        max_retry_count=max_retry_count,
        context=context,
        run_status=run_status,
    )


def publish_outbox_event_safely(
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


def _require_delivery_limit(limit: int) -> None:
    _require_positive(limit, "limit")
    if limit > OUTBOX_DELIVERY_RUN_ONCE_BATCH_CEILING:
        raise ValueError("limit exceeds outbox_delivery_run_once_batch_ceiling")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
