from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any


class IdempotencyDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IdempotencyPolicy:
    namespace: str
    ttl_seconds: int = 86_400


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    payload_hash: str


def tenant_scoped_idempotency_identity(tenant_id: str, idempotency_key: str) -> str:
    """Build an internal tenant/key identity without changing the caller's raw key."""
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be non-empty")
    if not idempotency_key or not idempotency_key.strip():
        raise ValueError("idempotency_key must be non-empty")
    # Length-prefixing is injective without using NUL, which PostgreSQL text
    # parameters reject even when the identity is used only for advisory locks.
    return f"tenant:{len(tenant_id)}:{tenant_id}{idempotency_key}"


def system_scoped_idempotency_identity(idempotency_key: str) -> str:
    """Keep system-only operations disjoint from every tenant namespace."""
    if not idempotency_key or not idempotency_key.strip():
        raise ValueError("idempotency_key must be non-empty")
    return f"system:{idempotency_key}"


def payload_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_idempotency(
    *,
    key: str,
    payload: dict[str, Any],
    existing: IdempotencyRecord | None,
) -> tuple[IdempotencyDecision, IdempotencyRecord]:
    record = IdempotencyRecord(key=key, payload_hash=payload_fingerprint(payload))
    if existing is None:
        return IdempotencyDecision.ACCEPTED, record
    if existing.key == key and existing.payload_hash == record.payload_hash:
        return IdempotencyDecision.REPLAYED, existing
    return IdempotencyDecision.CONFLICT, existing
