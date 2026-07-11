from __future__ import annotations

import os

from app.infrastructure.ed25519_lotus_ai_attestation_verifier import (
    Ed25519LotusAIAttestationSignatureVerifier,
)
from app.infrastructure.http_lotus_ai_attestation_keys import HttpLotusAIAttestationKeySource


LOTUS_AI_BASE_URL_ENV = "LOTUS_AI_BASE_URL"
LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS"

_KEY_SOURCE: HttpLotusAIAttestationKeySource | None = None
_SIGNATURE_VERIFIER = Ed25519LotusAIAttestationSignatureVerifier()


def get_lotus_ai_attestation_dependencies() -> tuple[
    HttpLotusAIAttestationKeySource,
    Ed25519LotusAIAttestationSignatureVerifier,
]:
    global _KEY_SOURCE
    if _KEY_SOURCE is None:
        base_url = os.getenv(LOTUS_AI_BASE_URL_ENV, "").strip()
        if not base_url:
            raise RuntimeError(f"{LOTUS_AI_BASE_URL_ENV} is required for attested AI output")
        _KEY_SOURCE = HttpLotusAIAttestationKeySource(
            base_url=base_url,
            timeout_seconds=_timeout_seconds(),
        )
    return _KEY_SOURCE, _SIGNATURE_VERIFIER


def close_lotus_ai_attestation_dependencies() -> None:
    global _KEY_SOURCE
    if _KEY_SOURCE is not None:
        _KEY_SOURCE.close()
        _KEY_SOURCE = None


def reset_lotus_ai_attestation_dependencies() -> None:
    close_lotus_ai_attestation_dependencies()


def _timeout_seconds() -> float:
    raw = os.getenv(LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV, "2.0").strip()
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV} must be numeric") from exc
    if timeout <= 0 or timeout > 10:
        raise RuntimeError(
            f"{LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV} must be greater than 0 and at most 10"
        )
    return timeout
