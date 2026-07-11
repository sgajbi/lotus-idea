from __future__ import annotations

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram


HTTP_REQUESTS_METRIC = "lotus_idea_http_requests_total"
HTTP_DURATION_METRIC = "lotus_idea_http_request_duration_seconds"
HTTP_METRIC_LABELS = ("method", "route", "status_class")
HTTP_DURATION_BUCKETS_SECONDS = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    1.5,
    2.5,
    5.0,
    10.0,
)


class ServiceSloMetrics:
    def __init__(self, registry: CollectorRegistry = REGISTRY) -> None:
        self._requests = Counter(
            HTTP_REQUESTS_METRIC,
            "Count of Lotus Idea HTTP requests by bounded route and outcome class.",
            HTTP_METRIC_LABELS,
            registry=registry,
        )
        self._duration = Histogram(
            HTTP_DURATION_METRIC,
            "Lotus Idea HTTP request duration by bounded route and outcome class.",
            HTTP_METRIC_LABELS,
            buckets=HTTP_DURATION_BUCKETS_SECONDS,
            registry=registry,
        )

    def observe_http_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        normalized_method = method.strip().upper()
        if not normalized_method:
            raise ValueError("method is required")
        if not route.startswith("/") or "?" in route:
            raise ValueError("route must be a route template without query string")
        if status_code < 100 or status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        labels = {
            "method": normalized_method,
            "route": route,
            "status_class": f"{status_code // 100}xx",
        }
        self._requests.labels(**labels).inc()
        self._duration.labels(**labels).observe(duration_seconds)


_SERVICE_SLO_METRICS = ServiceSloMetrics()


def observe_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    _SERVICE_SLO_METRICS.observe_http_request(
        method=method,
        route=route,
        status_code=status_code,
        duration_seconds=duration_seconds,
    )
