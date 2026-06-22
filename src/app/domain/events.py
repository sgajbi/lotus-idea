from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Mapping


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


class OutboxEventStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


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
    correlation_id: str | None = None
    causation_id: str | None = None
    published_at_utc: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = 0

    def __post_init__(self) -> None:
        _require_text(self.event_id, "event_id")
        _require_text(self.event_type, "event_type")
        _require_text(self.aggregate_type, "aggregate_type")
        _require_text(self.aggregate_id, "aggregate_id")
        _require_text(self.schema_version, "schema_version")
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")
        if self.published_at_utc is not None:
            _require_aware_utc(self.published_at_utc, "published_at_utc")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")
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
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> OutboxEventRecord:
    _require_aware_utc(occurred_at_utc, "occurred_at_utc")
    idempotency_fingerprint = (
        _fingerprint(idempotency_key) if idempotency_key is not None else None
    )
    event_id = _event_id(
        event_type=event_type,
        aggregate_id=aggregate_id,
        occurred_at_utc=occurred_at_utc,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    return OutboxEventRecord(
        event_id=event_id,
        event_type=event_type,
        aggregate_type="idea_candidate",
        aggregate_id=aggregate_id,
        schema_version="v1",
        payload=payload,
        occurred_at_utc=occurred_at_utc,
        idempotency_fingerprint=idempotency_fingerprint,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


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


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
