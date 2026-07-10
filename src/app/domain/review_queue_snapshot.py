from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.persistence_models import CandidatePersistenceRecord
from app.domain.scoring import QueueSnooze


REVIEW_QUEUE_SNAPSHOT_TOKEN_VERSION = "rqs1"
_REVIEW_QUEUE_SNAPSHOT_TOKEN_PATTERN = re.compile(r"^rqs1_[0-9a-f]{64}$")


class InvalidReviewQueueSnapshotTokenError(ValueError):
    """Raised when a caller supplies a malformed queue snapshot token."""


class ReviewQueueSnapshotTokenRequiredError(ValueError):
    """Raised when a continuation page has no queue snapshot token."""


class ReviewQueueSnapshotConflictError(RuntimeError):
    """Raised when queue state no longer matches the requested snapshot."""


@dataclass(frozen=True)
class ReviewQueueSnapshotIdentity:
    token: str
    fingerprint: str


def validate_review_queue_snapshot_token(token: str) -> str:
    normalized = token.strip()
    if not _REVIEW_QUEUE_SNAPSHOT_TOKEN_PATTERN.fullmatch(normalized):
        raise InvalidReviewQueueSnapshotTokenError(
            "snapshot_token must be an opaque review queue snapshot token"
        )
    return normalized


def visible_review_queue_candidate_records(
    records: tuple[CandidatePersistenceRecord, ...],
    *,
    evaluated_at_utc: datetime,
) -> tuple[CandidatePersistenceRecord, ...]:
    _require_aware_datetime(evaluated_at_utc, "evaluated_at_utc")
    return tuple(
        record for record in records if record.candidate.created_at_utc <= evaluated_at_utc
    )


def review_queue_candidate_fingerprint(
    records: tuple[CandidatePersistenceRecord, ...],
) -> str:
    material = tuple(
        {
            "candidate": record.candidate,
            "evidenceHash": record.evidence_hash,
        }
        for record in sorted(records, key=lambda item: item.candidate.candidate_id)
    )
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def build_review_queue_snapshot_identity(
    *,
    fingerprint: str,
    evaluated_at_utc: datetime,
    policy_version: str,
    access_scope_filter: QueueAccessScopeFilter | None,
    snoozes: tuple[QueueSnooze, ...] = (),
) -> ReviewQueueSnapshotIdentity:
    _require_aware_datetime(evaluated_at_utc, "evaluated_at_utc")
    if not fingerprint.strip():
        raise ValueError("fingerprint is required")
    if not policy_version.strip():
        raise ValueError("policy_version is required")
    token_material = {
        "accessScopeFilter": access_scope_filter,
        "candidateFingerprint": fingerprint,
        "evaluatedAtUtc": evaluated_at_utc,
        "policyVersion": policy_version,
        "snoozes": tuple(snoozes),
        "tokenVersion": REVIEW_QUEUE_SNAPSHOT_TOKEN_VERSION,
    }
    digest = hashlib.sha256(_canonical_json(token_material).encode("utf-8")).hexdigest()
    return ReviewQueueSnapshotIdentity(
        token=f"{REVIEW_QUEUE_SNAPSHOT_TOKEN_VERSION}_{digest}",
        fingerprint=fingerprint,
    )


def require_matching_review_queue_snapshot(
    *,
    expected_token: str | None,
    actual_token: str,
) -> None:
    if expected_token is None:
        return
    if validate_review_queue_snapshot_token(expected_token) != actual_token:
        raise ReviewQueueSnapshotConflictError(
            "advisor review queue state changed after the requested snapshot"
        )


def _canonical_json(value: object) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_value(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported review queue snapshot value: {type(value).__name__}")


def _require_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
