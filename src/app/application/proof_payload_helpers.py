from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any


def source_safe_mapping_digest(payload: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{hashlib.sha256(rendered.encode('utf-8')).hexdigest()}"


def non_empty_text_array(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )
