from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

import httpx

from app.ports.capacity_probe import CapacityProbeRequest, CapacityProbeResult


ALLOWED_RESPONSE_FIELDS = frozenset(
    {
        "attemptedCount",
        "blocker",
        "deliveredCount",
        "deliveryReadyCount",
        "durableStorageBacked",
        "failedCount",
        "maxRetryCount",
        "oldestDeliveryReadyAgeSeconds",
        "retryDeferredCount",
        "runStatus",
        "totalCount",
    }
)


class HttpCapacityProbe:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
        monotonic: Callable[[], float] = time.perf_counter,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )
        self._monotonic = monotonic

    def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult:
        started_at = self._monotonic()
        try:
            response = self._client.request(
                request.method,
                request.path,
                headers=dict(request.headers),
            )
        except httpx.TimeoutException:
            return self._result(started_at, None, "timeout", {})
        except httpx.TransportError:
            return self._result(started_at, None, "unavailable", {})
        outcome = (
            "accepted" if response.status_code in request.expected_status_codes else "rejected"
        )
        return self._result(
            started_at,
            response.status_code,
            outcome,
            _bounded_response_summary(response),
        )

    def close(self) -> None:
        self._client.close()

    def _result(
        self,
        started_at: float,
        status_code: int | None,
        transport_outcome: str,
        response_summary: dict[str, object],
    ) -> CapacityProbeResult:
        return CapacityProbeResult(
            duration_seconds=max(0.0, self._monotonic() - started_at),
            status_code=status_code,
            transport_outcome=transport_outcome,
            response_summary=response_summary,
        )


def _bounded_response_summary(response: httpx.Response) -> dict[str, object]:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type and "application/problem+json" not in content_type:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    if not isinstance(payload, dict):
        return {}
    summary: dict[str, object] = {}
    for key, value in payload.items():
        bounded = _bounded_value(value)
        if key in ALLOWED_RESPONSE_FIELDS and bounded is not None:
            summary[key] = bounded
    return summary


def _bounded_value(value: Any) -> object | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and 0 <= value <= 1_000_000:
        return value
    if isinstance(value, float) and 0 <= value <= 31_536_000:
        return value
    if isinstance(value, str) and value in {
        "blocked",
        "completed",
        "conflict",
        "replayed",
    }:
        return value
    if isinstance(value, list) and all(
        isinstance(item, str) and 0 < len(item) <= 100 for item in value
    ):
        return tuple(sorted(set(value)))
    return None
