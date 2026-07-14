from __future__ import annotations

import hashlib
from pathlib import Path
import re


_BARE_SHA256 = re.compile(r"[0-9a-f]{64}")
_CANONICAL_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def canonical_artifact_sha256(value: str | None, *, fallback_path: Path) -> str:
    if value is None:
        return f"sha256:{hashlib.sha256(fallback_path.read_bytes()).hexdigest()}"
    if _BARE_SHA256.fullmatch(value) is not None:
        return f"sha256:{value}"
    if _CANONICAL_SHA256.fullmatch(value) is not None:
        return value
    raise ValueError("artifact SHA-256 must be 64 lowercase hex characters")
