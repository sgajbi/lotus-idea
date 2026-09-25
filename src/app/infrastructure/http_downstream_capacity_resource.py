from __future__ import annotations

from typing import Any, Mapping

import httpx


MAX_RESPONSE_BYTES = 1_048_576


class HttpDownstreamCapacityResource:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        base_headers: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers=dict(base_headers or {}),
            transport=transport,
            follow_redirects=False,
        )

    def fetch_candidate_detail(
        self,
        *,
        candidate_id: str,
        tenant_id: str,
        book_id: str,
        portfolio_id: str,
        client_id: str,
    ) -> Mapping[str, Any]:
        return self._get_json(
            f"/api/v1/idea-candidates/{candidate_id}",
            headers={
                "X-Caller-Subject": "capacity-resource-selector",
                "X-Caller-Roles": "advisor",
                "X-Caller-Capabilities": "idea.candidate.detail.read",
                "X-Caller-Tenant-Ids": tenant_id,
                "X-Caller-Book-Ids": book_id,
                "X-Caller-Portfolio-Ids": portfolio_id,
                "X-Caller-Client-Ids": client_id,
                "X-Correlation-Id": f"capacity-resource-{candidate_id}",
            },
        )

    def close(self) -> None:
        self._client.close()

    def _get_json(self, path: str, *, headers: Mapping[str, str]) -> dict[str, Any]:
        try:
            response = self._client.get(path, headers=dict(headers))
        except httpx.HTTPError as exc:
            raise ValueError("capacity resource API request failed") from exc
        if response.status_code != 200:
            raise ValueError(f"capacity resource API returned status {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValueError("capacity resource API response exceeded size limit")
        try:
            body = response.json()
        except ValueError as exc:
            raise ValueError("capacity resource API returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ValueError("capacity resource API response must be an object")
        return body
