from __future__ import annotations

from typing import Mapping

import httpx

from app.domain.lotus_ai_run_attestation import LotusAIAttestationKeyDiscovery
from app.integration.lotus_ai_attestation_contract import (
    map_lotus_ai_attestation_key_discovery,
)


class HttpLotusAIAttestationKeySource:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("lotus-ai base URL is required")
        if timeout_seconds <= 0 or timeout_seconds > 10:
            raise ValueError("lotus-ai key-discovery timeout must be between 0 and 10 seconds")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    def get_key_discovery(self) -> LotusAIAttestationKeyDiscovery:
        try:
            response = self._client.get("/.well-known/lotus-ai-workflow-attestation-keys")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("lotus-ai attestation key discovery is unavailable") from exc
        if not isinstance(payload, Mapping):
            raise RuntimeError("lotus-ai attestation key discovery must return an object")
        try:
            return map_lotus_ai_attestation_key_discovery(payload)
        except ValueError as exc:
            raise RuntimeError("lotus-ai attestation key discovery contract is invalid") from exc

    def close(self) -> None:
        self._client.close()
