from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

from app.domain.outbox.delivery import (
    OutboxDeliveryResult,
    claim_outbox_events_for_delivery,
    mark_owned_outbox_event_failed,
    mark_owned_outbox_event_published,
    outbox_events_for_delivery,
)
from app.domain.outbox.events import (
    EventLineageContext,
    OutboxEventRecord,
    build_candidate_outbox_event,
)
from app.domain.outbox.recovery import (
    MAX_OUTBOX_RECOVERY_ATTEMPTS,
    OutboxDeadLetterSummary,
    OutboxRecoveryAuditRecord,
    OutboxRecoveryClaimResult,
    claim_dead_letter_for_recovery,
    dead_letter_summaries,
)


class InMemoryOutboxRepositoryMixin:
    _outbox_events: dict[str, OutboxEventRecord]
    _outbox_recovery_records: dict[str, OutboxRecoveryAuditRecord]

    def _append_outbox_event(
        self,
        *,
        event_type: str,
        aggregate_id: str,
        occurred_at_utc: datetime,
        payload: Mapping[str, str],
        idempotency_key: str,
        event_lineage: EventLineageContext | None,
    ) -> None:
        event = build_candidate_outbox_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at_utc=occurred_at_utc,
            payload=payload,
            idempotency_key=idempotency_key,
            lineage=event_lineage,
        )
        self._outbox_events[event.event_id] = event

    def outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        evaluated_at_utc: datetime | None = None,
    ) -> tuple[OutboxEventRecord, ...]:
        return outbox_events_for_delivery(
            self._outbox_events,
            limit=limit,
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc,
        )

    def claim_outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        lease_owner: str,
        lease_attempt_id: str,
        claimed_at_utc: datetime,
        lease_expires_at_utc: datetime,
    ) -> tuple[OutboxEventRecord, ...]:
        return claim_outbox_events_for_delivery(
            self._outbox_events,
            limit=limit,
            max_retry_count=max_retry_count,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            claimed_at_utc=claimed_at_utc,
            lease_expires_at_utc=lease_expires_at_utc,
        )

    def mark_outbox_event_published(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        published_at_utc: datetime,
    ) -> OutboxDeliveryResult:
        return mark_owned_outbox_event_published(
            self._outbox_events,
            event_id,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            published_at_utc=published_at_utc,
        )

    def mark_outbox_event_failed(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        failure_reason: str,
        failed_at_utc: datetime | None = None,
        max_retry_count: int = 3,
        next_attempt_at_utc: datetime | None = None,
    ) -> OutboxDeliveryResult:
        return mark_owned_outbox_event_failed(
            self._outbox_events,
            event_id,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            failure_reason=failure_reason,
            failed_at_utc=failed_at_utc or datetime.now(UTC),
            max_retry_count=max_retry_count,
            next_attempt_at_utc=next_attempt_at_utc,
        )

    def dead_letter_summaries(
        self,
        *,
        limit: int = 100,
    ) -> tuple[OutboxDeadLetterSummary, ...]:
        return dead_letter_summaries(self._outbox_events, limit=limit)

    def claim_dead_letter_for_recovery(
        self,
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
        return claim_dead_letter_for_recovery(
            self._outbox_events,
            self._outbox_recovery_records,
            support_reference=support_reference,
            idempotency_key=idempotency_key,
            request_payload=request_payload,
            actor_subject=actor_subject,
            reason=reason,
            change_reference=change_reference,
            requested_at_utc=requested_at_utc,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            lease_expires_at_utc=lease_expires_at_utc,
            max_recovery_attempts=max_recovery_attempts,
        )

    def outbox_recovery_audit_records(self) -> tuple[OutboxRecoveryAuditRecord, ...]:
        return tuple(self._outbox_recovery_records.values())
