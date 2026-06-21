from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class DownstreamClientConfigurationError(ValueError):
    pass


class DownstreamServiceError(Exception):
    def __init__(self, *, code: str, status_code: int | None = None) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class DownstreamClientConfig:
    base_url: str
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DownstreamClientConfigurationError(
                "Downstream base_url must be an absolute HTTP(S) URL."
            )
        if self.timeout_seconds <= 0:
            raise DownstreamClientConfigurationError("Downstream timeout_seconds must be positive.")


def build_trace_headers(*, correlation_id: str | None, trace_id: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if correlation_id:
        headers["X-Correlation-Id"] = correlation_id
    if trace_id:
        headers["X-Trace-Id"] = trace_id
    return headers


class DownstreamJsonClient:
    def __init__(self, config: DownstreamClientConfig, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    def get_json(
        self,
        path: str,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            path,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    def post_json(
        self,
        path: str,
        *,
        json_payload: dict[str, Any],
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            path,
            json_payload=json_payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(
                method,
                path,
                json=json_payload,
                headers=build_trace_headers(
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ),
            )
        except httpx.TimeoutException as exc:
            raise DownstreamServiceError(code="upstream_timeout") from exc
        except httpx.HTTPError as exc:
            raise DownstreamServiceError(code="upstream_unavailable") from exc

        if 400 <= response.status_code < 500:
            raise DownstreamServiceError(
                code="upstream_rejected_request", status_code=response.status_code
            )
        if response.status_code >= 500:
            raise DownstreamServiceError(
                code="upstream_unavailable", status_code=response.status_code
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise DownstreamServiceError(
                code="upstream_malformed_response", status_code=response.status_code
            ) from exc

        if not isinstance(payload, dict):
            raise DownstreamServiceError(
                code="upstream_malformed_response", status_code=response.status_code
            )
        return payload
