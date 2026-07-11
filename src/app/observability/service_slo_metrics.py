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
WORKFLOW_RUNS_METRIC = "lotus_idea_workflow_runs_total"
WORKFLOW_DURATION_METRIC = "lotus_idea_workflow_duration_seconds"
WORKFLOW_ITEMS_METRIC = "lotus_idea_workflow_items_total"
WORKFLOW_METRIC_LABELS = ("workflow", "outcome")
WORKFLOWS = frozenset({"source_ingestion", "outbox_delivery"})
WORKFLOW_OUTCOMES = frozenset({"accepted", "blocked", "conflict", "failed", "replayed"})
WORKFLOW_DURATION_BUCKETS_SECONDS = (
    0.01,
    0.05,
    0.1,
    0.5,
    1.0,
    2.5,
    5.0,
    15.0,
    60.0,
    300.0,
    600.0,
)
DEPENDENCY_REQUESTS_METRIC = "lotus_idea_dependency_requests_total"
DEPENDENCY_DURATION_METRIC = "lotus_idea_dependency_request_duration_seconds"
DEPENDENCY_METRIC_LABELS = ("dependency", "method", "outcome")
DEPENDENCIES = frozenset(
    {
        "lotus-advise",
        "lotus-core-control",
        "lotus-core-query",
        "lotus-manage",
        "lotus-performance",
        "lotus-platform-broker",
        "lotus-report",
        "lotus-risk",
    }
)
DEPENDENCY_OUTCOMES = frozenset({"accepted", "malformed", "rejected", "timeout", "unavailable"})
DEPENDENCY_DURATION_BUCKETS_SECONDS = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
)
POSTGRES_OPERATIONS_METRIC = "lotus_idea_postgres_operations_total"
POSTGRES_DURATION_METRIC = "lotus_idea_postgres_operation_duration_seconds"
POSTGRES_METRIC_LABELS = ("operation", "outcome")
POSTGRES_OPERATIONS = frozenset(
    {"lifecycle_action", "mutation", "projection_read", "snapshot_read"}
)
POSTGRES_OUTCOMES = frozenset({"accepted", "conflict", "failed"})
POSTGRES_DURATION_BUCKETS_SECONDS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
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
        self._workflow_runs = Counter(
            WORKFLOW_RUNS_METRIC,
            "Count of bounded Lotus Idea background and operator workflow runs.",
            WORKFLOW_METRIC_LABELS,
            registry=registry,
        )
        self._workflow_duration = Histogram(
            WORKFLOW_DURATION_METRIC,
            "Lotus Idea workflow duration by governed workflow and outcome.",
            WORKFLOW_METRIC_LABELS,
            buckets=WORKFLOW_DURATION_BUCKETS_SECONDS,
            registry=registry,
        )
        self._workflow_items = Counter(
            WORKFLOW_ITEMS_METRIC,
            "Count of bounded items considered by Lotus Idea workflows.",
            WORKFLOW_METRIC_LABELS,
            registry=registry,
        )
        self._dependency_requests = Counter(
            DEPENDENCY_REQUESTS_METRIC,
            "Count of logical Lotus Idea dependency requests after bounded retries.",
            DEPENDENCY_METRIC_LABELS,
            registry=registry,
        )
        self._dependency_duration = Histogram(
            DEPENDENCY_DURATION_METRIC,
            "Lotus Idea logical dependency request duration including bounded retries.",
            DEPENDENCY_METRIC_LABELS,
            buckets=DEPENDENCY_DURATION_BUCKETS_SECONDS,
            registry=registry,
        )
        self._postgres_operations = Counter(
            POSTGRES_OPERATIONS_METRIC,
            "Count of bounded Lotus Idea PostgreSQL operations.",
            POSTGRES_METRIC_LABELS,
            registry=registry,
        )
        self._postgres_duration = Histogram(
            POSTGRES_DURATION_METRIC,
            "Lotus Idea PostgreSQL operation duration by bounded operation and outcome.",
            POSTGRES_METRIC_LABELS,
            buckets=POSTGRES_DURATION_BUCKETS_SECONDS,
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

    def observe_workflow_run(
        self,
        *,
        workflow: str,
        outcome: str,
        duration_seconds: float,
        item_count: int,
    ) -> None:
        if workflow not in WORKFLOWS:
            raise ValueError("workflow is not governed")
        if outcome not in WORKFLOW_OUTCOMES:
            raise ValueError("workflow outcome is not governed")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        if isinstance(item_count, bool) or not isinstance(item_count, int) or item_count < 0:
            raise ValueError("item_count must be a non-negative integer")
        labels = {"workflow": workflow, "outcome": outcome}
        self._workflow_runs.labels(**labels).inc()
        self._workflow_duration.labels(**labels).observe(duration_seconds)
        self._workflow_items.labels(**labels).inc(item_count)

    def observe_dependency_request(
        self,
        *,
        dependency: str,
        method: str,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        if dependency not in DEPENDENCIES:
            raise ValueError("dependency is not governed")
        normalized_method = method.strip().upper()
        if normalized_method not in {"GET", "POST"}:
            raise ValueError("dependency method is not governed")
        if outcome not in DEPENDENCY_OUTCOMES:
            raise ValueError("dependency outcome is not governed")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        labels = {
            "dependency": dependency,
            "method": normalized_method,
            "outcome": outcome,
        }
        self._dependency_requests.labels(**labels).inc()
        self._dependency_duration.labels(**labels).observe(duration_seconds)

    def observe_postgres_operation(
        self,
        *,
        operation: str,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        if operation not in POSTGRES_OPERATIONS:
            raise ValueError("PostgreSQL operation is not governed")
        if outcome not in POSTGRES_OUTCOMES:
            raise ValueError("PostgreSQL outcome is not governed")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        labels = {"operation": operation, "outcome": outcome}
        self._postgres_operations.labels(**labels).inc()
        self._postgres_duration.labels(**labels).observe(duration_seconds)


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


def observe_workflow_run(
    *,
    workflow: str,
    outcome: str,
    duration_seconds: float,
    item_count: int,
) -> None:
    _SERVICE_SLO_METRICS.observe_workflow_run(
        workflow=workflow,
        outcome=outcome,
        duration_seconds=duration_seconds,
        item_count=item_count,
    )


def observe_dependency_request(
    *,
    dependency: str,
    method: str,
    outcome: str,
    duration_seconds: float,
) -> None:
    _SERVICE_SLO_METRICS.observe_dependency_request(
        dependency=dependency,
        method=method,
        outcome=outcome,
        duration_seconds=duration_seconds,
    )


def observe_postgres_operation(
    *,
    operation: str,
    outcome: str,
    duration_seconds: float,
) -> None:
    _SERVICE_SLO_METRICS.observe_postgres_operation(
        operation=operation,
        outcome=outcome,
        duration_seconds=duration_seconds,
    )
