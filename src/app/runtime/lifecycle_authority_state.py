from __future__ import annotations

import os

from app.application.data_lifecycle.authority_verification import (
    LifecycleAuthoritySignatureVerifier,
)
from app.infrastructure.ed25519_signature_verifier import Ed25519SignatureVerifier
from app.infrastructure.http_lifecycle_authority_keys import HttpLifecycleAuthorityKeySource
from app.ports.data_lifecycle.authority import LifecycleAuthorityKeySource


LIFECYCLE_AUTHORITY_BASE_URL_ENV = "LOTUS_IDEA_LIFECYCLE_AUTHORITY_BASE_URL"
LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS"

_KEY_SOURCE: LifecycleAuthorityKeySource | None = None
_SIGNATURE_VERIFIER = Ed25519SignatureVerifier()


def get_lifecycle_authority_dependencies() -> tuple[
    LifecycleAuthorityKeySource,
    LifecycleAuthoritySignatureVerifier,
]:
    global _KEY_SOURCE
    if _KEY_SOURCE is None:
        base_url = os.getenv(LIFECYCLE_AUTHORITY_BASE_URL_ENV, "").strip()
        if not base_url:
            raise RuntimeError(
                f"{LIFECYCLE_AUTHORITY_BASE_URL_ENV} is required for signed lifecycle authority"
            )
        _KEY_SOURCE = HttpLifecycleAuthorityKeySource(
            base_url=base_url,
            timeout_seconds=_timeout_seconds(),
        )
    return _KEY_SOURCE, _SIGNATURE_VERIFIER


def close_lifecycle_authority_dependencies() -> None:
    global _KEY_SOURCE
    if _KEY_SOURCE is not None:
        _KEY_SOURCE.close()
        _KEY_SOURCE = None


def reset_lifecycle_authority_dependencies() -> None:
    close_lifecycle_authority_dependencies()


def _timeout_seconds() -> float:
    raw = os.getenv(LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV, "2.0").strip()
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV} must be numeric") from exc
    if timeout <= 0 or timeout > 10:
        raise RuntimeError(
            f"{LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV} must be greater than 0 and at most 10"
        )
    return timeout
