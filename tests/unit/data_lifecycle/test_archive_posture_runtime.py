from __future__ import annotations

import base64
from copy import deepcopy
import json
from typing import Any

import pytest

from app.runtime.data_lifecycle.archive_posture_state import (
    ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV,
    ArchiveLifecycleTrustUnavailableError,
    get_archive_lifecycle_dependencies,
)
from app.runtime.settings import RUNTIME_PROFILE_ENV


_PUBLIC_KEY = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")


def _trust_bundle() -> dict[str, Any]:
    return {
        "keys": [
            {
                "key_id": "archive-key-001",
                "algorithm": "ed25519",
                "public_key_base64": _PUBLIC_KEY,
                "provenance": "managed",
                "status": "active",
                "not_before_utc": "2026-07-01T00:00:00Z",
                "not_after_utc": None,
            }
        ],
    }


def test_runtime_loads_exact_archive_lifecycle_verification_keys_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV,
        json.dumps(_trust_bundle()),
    )

    keys, verifier = get_archive_lifecycle_dependencies()

    assert keys[0].key_id == "archive-key-001"
    assert keys[0].algorithm == "ed25519"
    assert keys[0].provenance == "managed"
    assert verifier is not None


def test_runtime_reconstruction_retains_exact_archive_trust_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, json.dumps(_trust_bundle()))

    first_keys, first_verifier = get_archive_lifecycle_dependencies()
    second_keys, second_verifier = get_archive_lifecycle_dependencies()

    assert second_keys == first_keys
    assert second_verifier is first_verifier


@pytest.mark.parametrize("profile", ["demo", "staging", "production"])
def test_runtime_rejects_ephemeral_archive_keys_outside_local_test(
    monkeypatch: pytest.MonkeyPatch,
    profile: str,
) -> None:
    payload = _trust_bundle()
    payload["keys"][0]["provenance"] = "ephemeral_development"
    monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, json.dumps(payload))
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, profile)

    with pytest.raises(ArchiveLifecycleTrustUnavailableError, match="invalid"):
        get_archive_lifecycle_dependencies()


@pytest.mark.parametrize("profile", ["local", "test"])
def test_runtime_allows_explicit_ephemeral_archive_keys_only_in_local_test(
    monkeypatch: pytest.MonkeyPatch,
    profile: str,
) -> None:
    payload = _trust_bundle()
    payload["keys"][0]["provenance"] = "ephemeral_development"
    monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, json.dumps(payload))
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, profile)

    keys, _ = get_archive_lifecycle_dependencies()

    assert keys[0].provenance == "ephemeral_development"


def test_runtime_rejects_incomplete_legacy_archive_key_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV,
        json.dumps(
            {
                "keys": [
                    {
                        "key_id": "archive-key-001",
                        "algorithm": "ed25519",
                        "public_key_base64": _PUBLIC_KEY,
                        "provenance": "managed",
                    }
                ]
            }
        ),
    )

    with pytest.raises(ArchiveLifecycleTrustUnavailableError, match="invalid"):
        get_archive_lifecycle_dependencies()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"algorithm": "rsa"}, "invalid"),
        ({"provenance": "self_asserted"}, "invalid"),
        ({"status": "unknown"}, "invalid"),
        ({"status": "revoked"}, "invalid"),
        ({"public_key_base64": "dG9vLXNob3J0"}, "invalid"),
        ({"public_key_base64": base64.b64encode(bytes([255]) * 32).decode("ascii")}, "invalid"),
        ({"public_key_base64": _PUBLIC_KEY.rstrip("=")}, "invalid"),
        ({"status": "retired", "not_after_utc": None}, "invalid"),
        ({"status": "active", "not_after_utc": "2026-08-01T00:00:00Z"}, "invalid"),
        ({"unexpected": True}, "invalid"),
    ],
)
def test_runtime_rejects_malformed_or_contradictory_archive_key_metadata(
    monkeypatch: pytest.MonkeyPatch,
    mutation: dict[str, object],
    expected: str,
) -> None:
    payload = deepcopy(_trust_bundle())
    payload["keys"][0].update(mutation)
    monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, json.dumps(payload))

    with pytest.raises(ArchiveLifecycleTrustUnavailableError, match=expected):
        get_archive_lifecycle_dependencies()


def test_runtime_rejects_duplicate_archive_key_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _trust_bundle()
    payload["keys"].append(deepcopy(payload["keys"][0]))
    monkeypatch.setenv(ARCHIVE_LIFECYCLE_TRUST_BUNDLE_ENV, json.dumps(payload))

    with pytest.raises(ArchiveLifecycleTrustUnavailableError, match="invalid"):
        get_archive_lifecycle_dependencies()


@pytest.mark.parametrize("value", ["", "not-json", '{"keys":[]}'])
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
