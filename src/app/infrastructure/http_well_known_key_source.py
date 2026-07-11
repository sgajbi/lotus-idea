from __future__ import annotations

from typing import Callable, Generic, Mapping, TypeVar

import httpx


_DiscoveryT = TypeVar("_DiscoveryT")


class HttpWellKnownKeySource(Generic[_DiscoveryT]):
    def __init__(
        self,
        *,
        base_url: str,
        discovery_path: str,
        contract_mapper: Callable[[Mapping[str, object]], _DiscoveryT],
        error_label: str,
        timeout_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError(f"{error_label} base URL is required")
        if timeout_seconds <= 0 or timeout_seconds > 10:
            raise ValueError(f"{error_label} timeout must be between 0 and 10 seconds")
        if not discovery_path.startswith("/.well-known/"):
            raise ValueError(f"{error_label} path must be a well-known path")
        self._discovery_path = discovery_path
        self._contract_mapper = contract_mapper
        self._error_label = error_label
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    def get_key_discovery(self) -> _DiscoveryT:
        try:
            response = self._client.get(self._discovery_path)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"{self._error_label} is unavailable") from exc
        if not isinstance(payload, Mapping):
            raise RuntimeError(f"{self._error_label} must return an object")
        try:
            return self._contract_mapper(payload)
        except ValueError as exc:
            raise RuntimeError(f"{self._error_label} contract is invalid") from exc

    def close(self) -> None:
        self._client.close()
