from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from app.observability.service_slo_metrics import (
    HTTP_DURATION_BUCKETS_SECONDS,
    HTTP_METRIC_LABELS,
    ServiceSloMetrics,
    WORKFLOW_METRIC_LABELS,
    WORKFLOW_OUTCOMES,
    WORKFLOWS,
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


def test_workflow_sli_metrics_capture_duration_and_throughput_with_closed_labels() -> None:
    registry = CollectorRegistry()
    metrics = ServiceSloMetrics(registry)

    metrics.observe_workflow_run(
        workflow="source_ingestion",
        outcome="accepted",
        duration_seconds=1.25,
        item_count=8,
    )
    payload = generate_latest(registry).decode("utf-8")

    assert WORKFLOW_METRIC_LABELS == ("workflow", "outcome")
    assert WORKFLOWS == {"source_ingestion", "outbox_delivery"}
    assert WORKFLOW_OUTCOMES == {"accepted", "blocked", "conflict", "failed", "replayed"}
    assert 'workflow="source_ingestion"' in payload
    assert 'outcome="accepted"' in payload
    assert "lotus_idea_workflow_duration_seconds_sum" in payload
    assert "lotus_idea_workflow_items_total" in payload
    assert "tenant" not in payload


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"workflow": "portfolio_rebalance"}, "workflow is not governed"),
        ({"outcome": "client-123"}, "workflow outcome is not governed"),
        ({"duration_seconds": -1.0}, "duration_seconds must be non-negative"),
        ({"item_count": True}, "item_count must be a non-negative integer"),
    ],
)
def test_workflow_sli_metrics_reject_unbounded_or_invalid_observations(
    changes: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "workflow": "outbox_delivery",
        "outcome": "accepted",
        "duration_seconds": 0.5,
        "item_count": 1,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        ServiceSloMetrics(CollectorRegistry()).observe_workflow_run(**values)  # type: ignore[arg-type]
