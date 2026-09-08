"""Deterministic, valid evidence digests for test fixtures."""

from __future__ import annotations

import hashlib


def evidence_digest(*identity_parts: object) -> str:
    """Return a SHA-256 digest while keeping fixture identities readable."""

    identity = "|".join(str(part) for part in identity_parts)
    return f"sha256:{hashlib.sha256(identity.encode()).hexdigest()}"
