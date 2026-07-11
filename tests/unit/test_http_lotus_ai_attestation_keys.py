from __future__ import annotations

import httpx
import pytest

from app.infrastructure.http_lotus_ai_attestation_keys import (
    HttpLotusAIAttestationKeySource,
)


def _discovery_payload() -> dict[str, object]:
    return {
        "schema_version": "lotus-ai.workflow-run-attestation-keys.v1",
        "issuer": "lotus-ai",
        "keys": [
            {
                "key_id": "attestation-key-1",
                "algorithm": "EdDSA",
                "curve": "Ed25519",
                "public_key_base64url": "cHVibGljLWtleQ",
                "rotation_epoch": 1,
                "status": "active",
                "not_before_utc": "2026-07-01T00:00:00Z",
                "not_after_utc": None,
            }
        ],
    }


def test_fetches_keys_only_from_configured_well_known_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://lotus-ai.internal/.well-known/lotus-ai-workflow-attestation-keys"
        )
        return httpx.Response(200, json=_discovery_payload())

    source = HttpLotusAIAttestationKeySource(
        base_url="https://lotus-ai.internal",
        transport=httpx.MockTransport(handler),
    )

    discovery = source.get_key_discovery()
    source.close()

    assert discovery.issuer == "lotus-ai"
    assert discovery.keys[0].key_id == "attestation-key-1"
    assert discovery.keys[0].status == "active"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://attacker.example/keys"}),
        httpx.Response(503, json={"detail": "unavailable"}),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={**_discovery_payload(), "unexpected": True}),
    ],
)
def test_key_discovery_fails_closed_for_redirect_status_or_invalid_contract(
    response: httpx.Response,
) -> None:
    source = HttpLotusAIAttestationKeySource(
        base_url="https://lotus-ai.internal",
        transport=httpx.MockTransport(lambda _: response),
    )

    with pytest.raises(RuntimeError, match="key discovery"):
        source.get_key_discovery()
    source.close()
