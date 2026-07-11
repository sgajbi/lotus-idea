from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import math

import httpx
from prometheus_client.parser import text_string_to_metric_families

from app.ports.resource_probe import ProcessResourceSnapshot, ResourceProbeError


MAXIMUM_METRICS_RESPONSE_BYTES = 1_048_576
REQUIRED_METRICS = (
    "process_cpu_seconds_total",
    "process_resident_memory_bytes",
)
OPTIONAL_METRICS = (
    "process_virtual_memory_bytes",
    "process_open_fds",
    "process_max_fds",
)


class PrometheusResourceProbe:
    def __init__(
        self,
        *,
        metrics_url: str,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not metrics_url.strip():
            raise ValueError("metrics_url must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._metrics_url = metrics_url
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=False)
        self._owns_client = client is None
        self._now = now

    def execute(self) -> ProcessResourceSnapshot:
        try:
            response = self._client.get(self._metrics_url)
            response.raise_for_status()
            if len(response.content) > MAXIMUM_METRICS_RESPONSE_BYTES:
                raise ResourceProbeError("resource metrics response exceeds the size limit")
            values = _metric_values(response.text)
            return ProcessResourceSnapshot(
                observed_at_utc=self._now(),
                cpu_seconds_total=values["process_cpu_seconds_total"],
                resident_memory_bytes=_whole_number(
                    values["process_resident_memory_bytes"],
                    "process_resident_memory_bytes",
                ),
                virtual_memory_bytes=_optional_whole_number(
                    values.get("process_virtual_memory_bytes"),
                    "process_virtual_memory_bytes",
                ),
                open_file_descriptors=_optional_whole_number(
                    values.get("process_open_fds"), "process_open_fds"
                ),
                max_file_descriptors=_optional_whole_number(
                    values.get("process_max_fds"), "process_max_fds"
                ),
            )
        except ResourceProbeError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ResourceProbeError("resource metrics collection failed") from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def _metric_values(payload: str) -> dict[str, float]:
    requested = set(REQUIRED_METRICS + OPTIONAL_METRICS)
    values: dict[str, float] = {}
    for family in text_string_to_metric_families(payload):
        for sample in family.samples:
            if sample.name not in requested:
                continue
            if sample.labels or sample.name in values:
                raise ResourceProbeError("resource metric cardinality is not singular")
            value = float(sample.value)
            if not math.isfinite(value) or value < 0:
                raise ResourceProbeError("resource metric value is invalid")
            values[sample.name] = value
    missing = sorted(set(REQUIRED_METRICS) - set(values))
    if missing:
        raise ResourceProbeError("required resource metrics are missing")
    if ("process_open_fds" in values) != ("process_max_fds" in values):
        raise ResourceProbeError("file descriptor resource metrics are incomplete")
    return values


def _whole_number(value: float, metric: str) -> int:
    if not value.is_integer():
        raise ResourceProbeError(f"{metric} must be a whole number")
    return int(value)


def _optional_whole_number(value: float | None, metric: str) -> int | None:
    return None if value is None else _whole_number(value, metric)
