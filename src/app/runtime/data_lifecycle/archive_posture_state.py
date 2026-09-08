from __future__ import annotations

import json
import os

from app.application.ed25519_key_trust import Ed25519SignatureVerifier as SignatureVerifierPort
from app.domain.data_lifecycle.archive_posture import (
    ArchiveLifecycleKeyProvenance,
    ArchiveLifecycleTrustRefusal,
    ArchiveLifecycleTrustRefusalReason,
    ArchiveLifecycleTrustedKey,
)
from app.infrastructure.ed25519_signature_verifier import Ed25519SignatureVerifier
from app.integration.data_lifecycle.archive_posture_contract import (
    map_archive_lifecycle_trust_bundle,
)
from app.runtime.settings import RuntimeProfile, load_runtime_settings


ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV = "LOTUS_IDEA_ARCHIVE_LIFECYCLE_TRUST_BUNDLE_JSON"

_SIGNATURE_VERIFIER = Ed25519SignatureVerifier()


class ArchiveLifecycleTrustUnavailableError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        reason: ArchiveLifecycleTrustRefusalReason | None = None,
    ) -> None:
        RuntimeError.__init__(self, message)
        self.reason = reason


def get_archive_lifecycle_dependencies() -> tuple[
    tuple[ArchiveLifecycleTrustedKey, ...],
    SignatureVerifierPort,
]:
    raw = os.getenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, "").strip()
    if not raw:
        raise ArchiveLifecycleTrustUnavailableError(
            f"{ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV} is required for Archive lifecycle posture"
        )
    try:
        payload = json.loads(raw)
        keys = map_archive_lifecycle_trust_bundle(payload)
        runtime_profile = load_runtime_settings().runtime_profile
        if runtime_profile not in {RuntimeProfile.LOCAL, RuntimeProfile.TEST} and any(
            key.provenance is not ArchiveLifecycleKeyProvenance.MANAGED for key in keys
        ):
            raise ValueError(
                "ephemeral Archive lifecycle keys are restricted to local and test profiles"
            )
    except ArchiveLifecycleTrustRefusal as exc:
        raise ArchiveLifecycleTrustUnavailableError(
            "Archive lifecycle trust bundle is unusable",
            reason=exc.reason,
        ) from exc
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ArchiveLifecycleTrustUnavailableError(
            "Archive lifecycle trust bundle is invalid"
        ) from exc
    return keys, _SIGNATURE_VERIFIER
