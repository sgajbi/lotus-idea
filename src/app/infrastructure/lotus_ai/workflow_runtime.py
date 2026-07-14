from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


class LotusAIWorkflowRuntimeUnavailable(RuntimeError):
    """Raised when the governed Lotus AI workflow runtime cannot be reached."""


class InvalidLotusAIWorkflowRuntimeResponse(RuntimeError):
    """Raised when Lotus AI returns a non-object or unsuccessful response."""


class HttpLotusAIWorkflowRuntime:
    _EXECUTION_PATH = "/platform/workflow-packs/execute"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/") + "/"
        parsed = urlparse(normalized_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("lotus-ai base URL must be an absolute HTTP(S) URL")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("lotus-ai runtime timeout must be greater than 0 and at most 30")
        self._endpoint = urljoin(normalized_base_url, self._EXECUTION_PATH.lstrip("/"))
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]:
        try:
            response = self._client.post(
                self._endpoint,
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
        if response.status_code != 200:
            raise InvalidLotusAIWorkflowRuntimeResponse(
                f"lotus-ai workflow execution returned HTTP {response.status_code}"
            )
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise InvalidLotusAIWorkflowRuntimeResponse(
                "lotus-ai workflow execution returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidLotusAIWorkflowRuntimeResponse(
                "lotus-ai workflow execution response must be an object"
            )
        return payload


__all__ = [
    "HttpLotusAIWorkflowRuntime",
    "InvalidLotusAIWorkflowRuntimeResponse",
    "LotusAIWorkflowRuntimeUnavailable",
]
