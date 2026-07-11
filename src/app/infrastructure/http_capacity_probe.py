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
        "code",
        "deliveredCount",
        "deliveryReadyCount",
        "durableStorageBacked",
        "failedCount",
        "maxRetryCount",
        "oldestDeliveryReadyAgeSeconds",
        "retryDeferredCount",
        "runStatus",
        "sourceFailureCounts",
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
        bounded = _bounded_value(key, value)
        if key in ALLOWED_RESPONSE_FIELDS and bounded is not None:
            summary[key] = bounded
    return summary


def _bounded_value(key: str, value: Any) -> object | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and 0 <= value <= 1_000_000:
        return value
    if isinstance(value, float) and 0 <= value <= 31_536_000:
        return value
    if isinstance(value, str):
        if key == "runStatus" and value in {"blocked", "completed", "conflict", "replayed"}:
            return value
        if key in {"code", "blocker"} and value in {
            "source_dependency_unavailable",
            "source_dependency_entitlement_denied",
        }:
            return value
        return None
    if key == "sourceFailureCounts" and isinstance(value, dict):
        expected = {"source_unavailable", "entitlement_denied", "other_blocked"}
        if set(value) != expected:
            return None
        if any(
            isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 1_000_000
            for count in value.values()
        ):
            return None
        return {failure_class: value[failure_class] for failure_class in sorted(expected)}
    if isinstance(value, list) and all(
        isinstance(item, str) and 0 < len(item) <= 100 for item in value
    ):
        return tuple(sorted(set(value)))
    return None
