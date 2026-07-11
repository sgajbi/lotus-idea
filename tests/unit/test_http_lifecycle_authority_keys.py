from __future__ import annotations

import httpx
import pytest

from app.infrastructure.http_lifecycle_authority_keys import (
    HttpLifecycleAuthorityKeySource,
)
from tests.support.lifecycle_authority_fixture import (
    lifecycle_authority_key_payload,
)


def test_fetches_lifecycle_keys_only_from_configured_well_known_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://lifecycle-authority.internal/.well-known/lotus-lifecycle-authority-keys"
        )
        return httpx.Response(200, json=lifecycle_authority_key_payload())

    source = HttpLifecycleAuthorityKeySource(
        base_url="https://lifecycle-authority.internal",
        transport=httpx.MockTransport(handler),
    )

    discovery = source.get_key_discovery()
    source.close()

    assert discovery.issuer == "bank-lifecycle-governance"
    assert discovery.keys[0].status == "active"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://attacker.example/keys"}),
        httpx.Response(503, json={"detail": "unavailable"}),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={**lifecycle_authority_key_payload(), "unexpected": True}),
    ],
)
def test_lifecycle_key_discovery_fails_closed_for_untrusted_response(
    response: httpx.Response,
) -> None:
    source = HttpLifecycleAuthorityKeySource(
        base_url="https://lifecycle-authority.internal",
        transport=httpx.MockTransport(lambda _: response),
    )

    with pytest.raises(RuntimeError, match="lifecycle authority key discovery"):
        source.get_key_discovery()
    source.close()
