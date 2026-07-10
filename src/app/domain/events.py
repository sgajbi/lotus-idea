from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Mapping

from app.domain.diagnostic_context import require_product_safe_context_id


FORBIDDEN_OUTBOX_PAYLOAD_KEYS = frozenset(
    {
        "account_id",
        "client_id",
        "client_name",
        "content_hash",
        "evidence_hash",
        "holding_id",
        "idempotency_key",
        "portfolio_id",
        "raw_source_payload",
        "request_body",
        "response_body",
        "route",
        "source_route",
    }
)
OUTBOX_EVENT_SCHEMA_VERSION = "v1"
OUTBOX_EVENT_AGGREGATE_TYPE = "idea_candidate"
SUPPORTED_OUTBOX_EVENT_TYPES = (
    "idea.candidate.persisted.v1",
    "idea.lifecycle.transitioned.v1",
    "idea.review.decision_recorded.v1",
    "idea.feedback.recorded.v1",
    "idea.conversion.intent_requested.v1",
    "idea.conversion.outcome_recorded.v1",
    "idea.report_evidence_pack.requested.v1",
)


class OutboxEventStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    PUBLISHED = "published"


class EventLineageOrigin(StrEnum):
    REQUEST = "request"
    PARENT_EVENT = "parent_event"
    SYSTEM_GENERATED = "system_generated"
    LEGACY_MIGRATED = "legacy_migrated"


@dataclass(frozen=True)
class EventLineageContext:
    correlation_id: str
    trace_id: str
    causation_id: str | None = None
    origin: EventLineageOrigin = EventLineageOrigin.REQUEST

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "correlation_id",
            require_product_safe_context_id(self.correlation_id, "correlation_id"),
        )
        object.__setattr__(
            self,
            "trace_id",
            require_product_safe_context_id(self.trace_id, "trace_id"),
        )
        if self.causation_id is not None:
            object.__setattr__(
                self,
                "causation_id",
                require_product_safe_context_id(self.causation_id, "causation_id"),
            )
        if self.origin is EventLineageOrigin.PARENT_EVENT and self.causation_id is None:
            raise ValueError("causation_id is required for parent_event lineage")
        if self.causation_id is not None and self.origin not in {
            EventLineageOrigin.PARENT_EVENT,
            EventLineageOrigin.LEGACY_MIGRATED,
        }:
            raise ValueError("causation_id is allowed only for parent_event lineage")


@dataclass(frozen=True)
class OutboxEventRecord:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    schema_version: str
    payload: Mapping[str, str]
    occurred_at_utc: datetime
    status: OutboxEventStatus = OutboxEventStatus.PENDING
    idempotency_fingerprint: str | None = None
    correlation_id: str = ""
    trace_id: str = ""
    causation_id: str | None = None
    lineage_origin: EventLineageOrigin = EventLineageOrigin.SYSTEM_GENERATED
    published_at_utc: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = 0
    first_failed_at_utc: datetime | None = None
    last_failed_at_utc: datetime | None = None
    next_attempt_at_utc: datetime | None = None
    lease_owner: str | None = None
    lease_attempt_id: str | None = None
    lease_expires_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.event_id, "event_id")
        _require_text(self.event_type, "event_type")
        _require_text(self.aggregate_type, "aggregate_type")
        _require_text(self.aggregate_id, "aggregate_id")
        _require_text(self.schema_version, "schema_version")
        if self.event_type not in SUPPORTED_OUTBOX_EVENT_TYPES:
            raise ValueError(f"unsupported outbox event_type: {self.event_type}")
        if self.aggregate_type != OUTBOX_EVENT_AGGREGATE_TYPE:
            raise ValueError(f"unsupported outbox aggregate_type: {self.aggregate_type}")
        if self.schema_version != OUTBOX_EVENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported outbox schema_version: {self.schema_version}")
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")
        lineage = (
            _system_event_lineage(self.event_id)
            if not self.correlation_id and not self.trace_id
            else EventLineageContext(
                correlation_id=self.correlation_id,
                trace_id=self.trace_id,
                causation_id=self.causation_id,
                origin=self.lineage_origin,
            )
        )
        object.__setattr__(self, "correlation_id", lineage.correlation_id)
        object.__setattr__(self, "trace_id", lineage.trace_id)
        object.__setattr__(self, "causation_id", lineage.causation_id)
        object.__setattr__(self, "lineage_origin", lineage.origin)
        if self.published_at_utc is not None:
            _require_aware_utc(self.published_at_utc, "published_at_utc")
        if self.first_failed_at_utc is not None:
            _require_aware_utc(self.first_failed_at_utc, "first_failed_at_utc")
        if self.last_failed_at_utc is not None:
            _require_aware_utc(self.last_failed_at_utc, "last_failed_at_utc")
        if self.next_attempt_at_utc is not None:
            _require_aware_utc(self.next_attempt_at_utc, "next_attempt_at_utc")
        if self.lease_expires_at_utc is not None:
            _require_aware_utc(self.lease_expires_at_utc, "lease_expires_at_utc")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")
        if self.status is OutboxEventStatus.LEASED:
            _require_text(self.lease_owner or "", "lease_owner")
            _require_text(self.lease_attempt_id or "", "lease_attempt_id")
            if self.lease_expires_at_utc is None:
                raise ValueError("lease_expires_at_utc is required for leased outbox events")
        elif any(
            value is not None
            for value in (self.lease_owner, self.lease_attempt_id, self.lease_expires_at_utc)
        ):
            raise ValueError("lease metadata is allowed only for leased outbox events")
        if self.status is OutboxEventStatus.PUBLISHED and self.published_at_utc is None:
            raise ValueError("published_at_utc is required for published outbox events")
        if self.status in {OutboxEventStatus.FAILED, OutboxEventStatus.DEAD_LETTER}:
            _require_text(self.failure_reason or "", "failure_reason")
            if self.first_failed_at_utc is None:
                raise ValueError("first_failed_at_utc is required for failed outbox events")
            if self.last_failed_at_utc is None:
                raise ValueError("last_failed_at_utc is required for failed outbox events")
        elif self.status is OutboxEventStatus.LEASED:
            if (self.first_failed_at_utc is None) != (self.last_failed_at_utc is None):
                raise ValueError("leased outbox failure timing must include first and last failure")
            if self.next_attempt_at_utc is not None:
                raise ValueError("leased outbox events cannot have next_attempt_at_utc")
        elif self.status is OutboxEventStatus.PUBLISHED:
            if (self.first_failed_at_utc is None) != (self.last_failed_at_utc is None):
                raise ValueError(
                    "published outbox failure timing must include first and last failure"
                )
            if self.next_attempt_at_utc is not None:
                raise ValueError("published outbox events cannot have next_attempt_at_utc")
        elif any(
            value is not None
            for value in (
                self.first_failed_at_utc,
                self.last_failed_at_utc,
                self.next_attempt_at_utc,
            )
        ):
            raise ValueError("failure timing is allowed only for failed or leased outbox events")
        if self.status is OutboxEventStatus.FAILED and self.next_attempt_at_utc is None:
            raise ValueError("next_attempt_at_utc is required for retryable failed outbox events")
        if self.status is OutboxEventStatus.DEAD_LETTER and self.next_attempt_at_utc is not None:
            raise ValueError("dead-lettered outbox events cannot have next_attempt_at_utc")
        leaked = FORBIDDEN_OUTBOX_PAYLOAD_KEYS.intersection(self.payload)
        if leaked:
            raise ValueError(
                f"Outbox event payload contains sensitive keys: {', '.join(sorted(leaked))}"
            )
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


def build_candidate_outbox_event(
    *,
    event_type: str,
    aggregate_id: str,
    occurred_at_utc: datetime,
    payload: Mapping[str, str],
    idempotency_key: str | None = None,
    lineage: EventLineageContext | None = None,
) -> OutboxEventRecord:
    _require_aware_utc(occurred_at_utc, "occurred_at_utc")
    idempotency_fingerprint = _fingerprint(idempotency_key) if idempotency_key is not None else None
    event_id = _event_id(
        event_type=event_type,
        aggregate_id=aggregate_id,
        occurred_at_utc=occurred_at_utc,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    event_lineage = lineage or _system_event_lineage(event_id)
    return OutboxEventRecord(
        event_id=event_id,
        event_type=event_type,
        aggregate_type=OUTBOX_EVENT_AGGREGATE_TYPE,
        aggregate_id=aggregate_id,
        schema_version=OUTBOX_EVENT_SCHEMA_VERSION,
        payload=payload,
        occurred_at_utc=occurred_at_utc,
        idempotency_fingerprint=idempotency_fingerprint,
        correlation_id=event_lineage.correlation_id,
        trace_id=event_lineage.trace_id,
        causation_id=event_lineage.causation_id,
        lineage_origin=event_lineage.origin,
    )


def _system_event_lineage(event_id: str) -> EventLineageContext:
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:24]
    return EventLineageContext(
        correlation_id=f"corr-system-{digest}",
        trace_id=f"trace-system-{digest}",
        origin=EventLineageOrigin.SYSTEM_GENERATED,
    )


def lease_outbox_event(
    event: OutboxEventRecord,
    *,
    lease_owner: str,
    lease_attempt_id: str,
    lease_expires_at_utc: datetime,
) -> OutboxEventRecord:
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    _require_aware_utc(lease_expires_at_utc, "lease_expires_at_utc")
    return replace(
        event,
        status=OutboxEventStatus.LEASED,
        published_at_utc=None,
        failure_reason=event.failure_reason,
        first_failed_at_utc=event.first_failed_at_utc,
        last_failed_at_utc=event.last_failed_at_utc,
        next_attempt_at_utc=None,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=lease_expires_at_utc,
    )


def mark_outbox_event_published(
    event: OutboxEventRecord,
    *,
    published_at_utc: datetime,
) -> OutboxEventRecord:
    _require_aware_utc(published_at_utc, "published_at_utc")
    return replace(
        event,
        status=OutboxEventStatus.PUBLISHED,
        published_at_utc=published_at_utc,
        failure_reason=event.failure_reason,
        first_failed_at_utc=event.first_failed_at_utc,
        last_failed_at_utc=event.last_failed_at_utc,
        next_attempt_at_utc=None,
        lease_owner=None,
        lease_attempt_id=None,
        lease_expires_at_utc=None,
    )


def mark_outbox_event_failed(
    event: OutboxEventRecord,
    *,
    failure_reason: str,
    failed_at_utc: datetime,
    max_retry_count: int,
    next_attempt_at_utc: datetime | None,
) -> OutboxEventRecord:
    validate_outbox_failure_reason(failure_reason)
    _require_aware_utc(failed_at_utc, "failed_at_utc")
    _require_positive(max_retry_count, "max_retry_count")
    retry_count = event.retry_count + 1
    status = (
        OutboxEventStatus.DEAD_LETTER
        if retry_count >= max_retry_count
        else OutboxEventStatus.FAILED
    )
    if status is OutboxEventStatus.FAILED:
        if next_attempt_at_utc is None:
            raise ValueError("next_attempt_at_utc is required for retryable failed outbox events")
        _require_aware_utc(next_attempt_at_utc, "next_attempt_at_utc")
        if next_attempt_at_utc <= failed_at_utc:
            raise ValueError("next_attempt_at_utc must be after failed_at_utc")
    elif next_attempt_at_utc is not None:
        raise ValueError("dead-lettered outbox events cannot have next_attempt_at_utc")
    return replace(
        event,
        status=status,
        published_at_utc=None,
        failure_reason=failure_reason,
        retry_count=retry_count,
        first_failed_at_utc=event.first_failed_at_utc or failed_at_utc,
        last_failed_at_utc=failed_at_utc,
        next_attempt_at_utc=next_attempt_at_utc,
        lease_owner=None,
        lease_attempt_id=None,
        lease_expires_at_utc=None,
    )


def validate_outbox_failure_reason(failure_reason: str) -> None:
    _require_text(failure_reason, "failure_reason")
    _reject_sensitive_failure_reason(failure_reason)


def _event_id(
    *,
    event_type: str,
    aggregate_id: str,
    occurred_at_utc: datetime,
    idempotency_fingerprint: str | None,
) -> str:
    payload = {
        "aggregate_id": aggregate_id,
        "event_type": event_type,
        "idempotency_fingerprint": idempotency_fingerprint,
        "occurred_at_utc": occurred_at_utc.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"evt_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]}"


def _fingerprint(value: str) -> str:
    _require_text(value, "idempotency_key")
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


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


def _reject_sensitive_failure_reason(failure_reason: str) -> None:
    normalized = failure_reason.lower()
    leaked = sorted(key for key in FORBIDDEN_OUTBOX_PAYLOAD_KEYS if key in normalized)
    if leaked:
        raise ValueError(f"Outbox failure reason contains sensitive keys: {', '.join(leaked)}")
