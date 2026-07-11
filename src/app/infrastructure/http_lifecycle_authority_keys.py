from __future__ import annotations

import httpx

from app.domain.lifecycle_authority import (
    LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH,
    LifecycleAuthorityKeyDiscovery,
)
from app.infrastructure.http_well_known_key_source import HttpWellKnownKeySource
from app.integration.lifecycle_authority_contract import (
    map_lifecycle_authority_key_discovery,
)


class HttpLifecycleAuthorityKeySource(HttpWellKnownKeySource[LifecycleAuthorityKeyDiscovery]):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            discovery_path=LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH,
            contract_mapper=map_lifecycle_authority_key_discovery,
            error_label="lifecycle authority key discovery",
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
