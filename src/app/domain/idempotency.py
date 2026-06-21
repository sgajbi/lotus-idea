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
