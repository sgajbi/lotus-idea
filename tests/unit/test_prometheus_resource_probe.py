from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app.infrastructure.prometheus_resource_probe import (
    MAXIMUM_METRICS_RESPONSE_BYTES,
    PrometheusResourceProbe,
)
from app.ports.resource_probe import ResourceProbeError


OBSERVED_AT = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)


def _client(payload: str, *, status_code: int = 200) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, text=payload, request=request)
        )
    )


def test_collects_bounded_process_metrics_without_labels() -> None:
    probe = PrometheusResourceProbe(
        metrics_url="https://idea.example/metrics",
        client=_client(
            """
# TYPE process_cpu_seconds counter
process_cpu_seconds_total 12.5
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 1024
process_virtual_memory_bytes 4096
process_open_fds 5
process_max_fds 100
lotus_idea_http_requests_total{tenant_id="not-consumed"} 9
"""
        ),
        now=lambda: OBSERVED_AT,
    )

    snapshot = probe.execute()

    assert snapshot.observed_at_utc == OBSERVED_AT
    assert snapshot.cpu_seconds_total == 12.5
    assert snapshot.resident_memory_bytes == 1024
    assert snapshot.virtual_memory_bytes == 4096
    assert snapshot.open_file_descriptors == 5
    assert snapshot.max_file_descriptors == 100


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("process_cpu_seconds_total 1\n", "required resource metrics are missing"),
        (
            'process_cpu_seconds_total{worker="one"} 1\nprocess_resident_memory_bytes 1\n',
            "cardinality is not singular",
        ),
        (
            "process_cpu_seconds_total NaN\nprocess_resident_memory_bytes 1\n",
            "metric value is invalid",
        ),
        (
            "process_cpu_seconds_total 1\nprocess_resident_memory_bytes 1\nprocess_open_fds 1\n",
            "file descriptor resource metrics are incomplete",
        ),
        (
            "process_cpu_seconds_total 1\nprocess_resident_memory_bytes 1.5\n",
            "must be a whole number",
        ),
    ],
)
def test_fails_closed_on_missing_ambiguous_or_invalid_metrics(payload: str, message: str) -> None:
    probe = PrometheusResourceProbe(
        metrics_url="https://idea.example/metrics", client=_client(payload)
    )

    with pytest.raises(ResourceProbeError, match=message):
        probe.execute()


def test_fails_closed_on_http_failure_without_endpoint_detail() -> None:
    probe = PrometheusResourceProbe(
        metrics_url="https://sensitive.example/metrics",
        client=_client("failure detail", status_code=503),
    )

    with pytest.raises(ResourceProbeError, match="collection failed") as captured:
        probe.execute()

    assert "sensitive" not in str(captured.value)
    assert "failure detail" not in str(captured.value)


def test_rejects_oversized_metrics_response() -> None:
    probe = PrometheusResourceProbe(
        metrics_url="https://idea.example/metrics",
        client=_client("x" * (MAXIMUM_METRICS_RESPONSE_BYTES + 1)),
    )

    with pytest.raises(ResourceProbeError, match="exceeds the size limit"):
        probe.execute()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"metrics_url": " "}, "must not be blank"),
        ({"metrics_url": "https://idea.example/metrics", "timeout_seconds": 0}, "positive"),
    ],
)
def test_rejects_invalid_configuration(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PrometheusResourceProbe(**kwargs)  # type: ignore[arg-type]


def test_close_does_not_close_injected_client() -> None:
    client = _client("process_cpu_seconds_total 1\nprocess_resident_memory_bytes 1\n")
    probe = PrometheusResourceProbe(metrics_url="https://idea.example/metrics", client=client)

    probe.close()

    assert client.is_closed is False
    client.close()
