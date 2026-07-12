from __future__ import annotations

import json
import os

from app.domain.data_lifecycle.archive_posture import ArchiveLifecycleTrustedKey
from app.infrastructure.ed25519_signature_verifier import Ed25519SignatureVerifier
from app.integration.data_lifecycle.archive_posture_contract import (
    map_archive_lifecycle_trust_bundle,
)


ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV = "LOTUS_IDEA_ARCHIVE_LIFECYCLE_TRUST_BUNDLE_JSON"

_SIGNATURE_VERIFIER = Ed25519SignatureVerifier()


class ArchiveLifecycleTrustUnavailableError(RuntimeError):
    pass


def get_archive_lifecycle_dependencies() -> tuple[
    tuple[ArchiveLifecycleTrustedKey, ...],
    Ed25519SignatureVerifier,
]:
    raw = os.getenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, "").strip()
    if not raw:
        raise ArchiveLifecycleTrustUnavailableError(
            f"{ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV} is required for Archive lifecycle posture"
        )
    try:
        payload = json.loads(raw)
        keys = map_archive_lifecycle_trust_bundle(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ArchiveLifecycleTrustUnavailableError(
            "Archive lifecycle trust bundle is invalid"
        ) from exc
    return keys, _SIGNATURE_VERIFIER
