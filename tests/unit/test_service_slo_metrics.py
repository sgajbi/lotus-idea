from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from app.observability.service_slo_metrics import (
    HTTP_DURATION_BUCKETS_SECONDS,
    HTTP_METRIC_LABELS,
    ServiceSloMetrics,
)


def test_http_sli_metrics_use_bounded_route_and_status_labels() -> None:
    registry = CollectorRegistry()
    metrics = ServiceSloMetrics(registry)

    metrics.observe_http_request(
        method="get",
        route="/api/v1/idea-candidates/{candidateId}",
        status_code=200,
        duration_seconds=0.125,
    )
    payload = generate_latest(registry).decode("utf-8")

    assert HTTP_METRIC_LABELS == ("method", "route", "status_class")
    assert 0.5 in HTTP_DURATION_BUCKETS_SECONDS
    assert 1.5 in HTTP_DURATION_BUCKETS_SECONDS
    assert 'method="GET"' in payload
    assert 'route="/api/v1/idea-candidates/{candidateId}"' in payload
    assert 'status_class="2xx"' in payload
    assert "candidate-001" not in payload
    assert "tenant" not in payload


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"method": " "}, "method is required"),
        ({"route": "/candidate/abc?debug=true"}, "route must be a route template"),
        ({"status_code": 700}, "valid HTTP status"),
        ({"duration_seconds": -0.1}, "must be non-negative"),
    ],
)
def test_http_sli_metrics_reject_unbounded_or_invalid_observations(
    changes: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "method": "GET",
        "route": "/health",
        "status_code": 200,
        "duration_seconds": 0.01,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        ServiceSloMetrics(CollectorRegistry()).observe_http_request(**values)  # type: ignore[arg-type]
