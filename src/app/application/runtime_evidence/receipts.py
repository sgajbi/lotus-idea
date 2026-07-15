from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from app.domain import SourceRef


def source_ref_receipt(ref: SourceRef | None) -> dict[str, Any] | None:
    if ref is None:
        return None
    material = {
        "productId": ref.product_id,
        "sourceSystem": ref.source_system.value,
        "productVersion": ref.product_version,
        "route": ref.route,
        "asOfDate": ref.as_of_date.isoformat(),
        "generatedAtUtc": format_utc(ref.generated_at_utc),
        "contentHash": ref.content_hash,
        "dataQualityStatus": ref.data_quality_status,
        "freshness": ref.freshness.value,
    }
    return {**material, "receiptDigest": sha256_json(material)}


def identity_hash(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.strip().encode('utf-8')).hexdigest()}"


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
