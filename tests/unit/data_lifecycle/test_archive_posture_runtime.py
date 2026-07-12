from __future__ import annotations

import json

import pytest

from app.runtime.data_lifecycle.archive_posture_state import (
    ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV,
    ArchiveLifecycleTrustUnavailableError,
    get_archive_lifecycle_dependencies,
)


def test_runtime_loads_strict_archive_consumer_trust_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV,
        json.dumps(
            {
                "schema_version": "lotus-idea.archive-lifecycle-trust-bundle.v1",
                "keys": [
                    {
                        "key_id": "archive-key-001",
                        "public_key_base64url": "cHVibGljLWtleQ",
                        "status": "active",
                        "not_before_utc": "2026-07-01T00:00:00Z",
                        "not_after_utc": None,
                    }
                ],
            }
        ),
    )

    keys, verifier = get_archive_lifecycle_dependencies()

    assert keys[0].key_id == "archive-key-001"
    assert verifier is not None


@pytest.mark.parametrize("value", ["", "not-json", '{"schema_version":"wrong"}'])
def test_runtime_fails_closed_for_missing_or_invalid_archive_trust(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    if value:
        monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, value)
    else:
        monkeypatch.delenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, raising=False)

    with pytest.raises(ArchiveLifecycleTrustUnavailableError):
        get_archive_lifecycle_dependencies()
