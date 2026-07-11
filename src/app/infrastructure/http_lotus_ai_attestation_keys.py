from __future__ import annotations

import httpx

from app.domain.lotus_ai_run_attestation import LotusAIAttestationKeyDiscovery
from app.infrastructure.http_well_known_key_source import HttpWellKnownKeySource
from app.integration.lotus_ai_attestation_contract import (
    map_lotus_ai_attestation_key_discovery,
)


class HttpLotusAIAttestationKeySource(HttpWellKnownKeySource[LotusAIAttestationKeyDiscovery]):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            discovery_path="/.well-known/lotus-ai-workflow-attestation-keys",
            contract_mapper=map_lotus_ai_attestation_key_discovery,
            error_label="lotus-ai attestation key discovery",
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
