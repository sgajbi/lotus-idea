from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx


class LotusAIWorkflowRuntimeUnavailable(RuntimeError):
    """Raised when the governed Lotus AI workflow runtime cannot be reached."""


class InvalidLotusAIWorkflowRuntimeResponse(RuntimeError):
    """Raised when Lotus AI returns a non-object or unsuccessful response."""


class HttpLotusAIWorkflowRuntime:
    _EXECUTION_PATH = "/platform/workflow-packs/execute"
    _ATTESTATION_PATH_TEMPLATE = "/platform/workflow-packs/runs/{run_id}/attestation"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/") + "/"
        parsed = urlparse(normalized_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("lotus-ai base URL must be an absolute HTTP(S) URL")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("lotus-ai runtime timeout must be greater than 0 and at most 30")
        self._base_url = normalized_base_url
        self._execution_endpoint = urljoin(normalized_base_url, self._EXECUTION_PATH.lstrip("/"))
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]:
        try:
            response = await self._client.post(
                self._execution_endpoint,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Caller-App": caller_app,
                },
                json=dict(request),
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise LotusAIWorkflowRuntimeUnavailable(
                "lotus-ai workflow runtime is unavailable"
            ) from exc
        return self._response_object(response, operation="workflow execution")

    async def get_run_attestation(self, run_id: str) -> Mapping[str, object]:
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            raise ValueError("lotus-ai workflow run id must not be empty")
        endpoint = urljoin(
            self._base_url,
            self._ATTESTATION_PATH_TEMPLATE.format(run_id=quote(normalized_run_id, safe="")).lstrip(
                "/"
            ),
        )
        try:
            response = await self._client.get(
                endpoint,
                headers={"Accept": "application/json"},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise LotusAIWorkflowRuntimeUnavailable(
                "lotus-ai workflow runtime is unavailable"
            ) from exc
        return self._response_object(response, operation="run attestation")

    @staticmethod
    def _response_object(
        response: httpx.Response,
        *,
        operation: str,
    ) -> Mapping[str, object]:
        if response.status_code != 200:
            raise InvalidLotusAIWorkflowRuntimeResponse(
                f"lotus-ai {operation} returned HTTP {response.status_code}"
            )
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise InvalidLotusAIWorkflowRuntimeResponse(
                f"lotus-ai {operation} returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidLotusAIWorkflowRuntimeResponse(
                f"lotus-ai {operation} response must be an object"
            )
        return payload


__all__ = [
    "HttpLotusAIWorkflowRuntime",
    "InvalidLotusAIWorkflowRuntimeResponse",
    "LotusAIWorkflowRuntimeUnavailable",
]
