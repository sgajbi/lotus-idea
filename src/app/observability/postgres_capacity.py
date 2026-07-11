from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import Lock

from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_client.core import GaugeMetricFamily, Metric

from app.domain.capacity_posture import CapacityPosture, PostgresCapacityPosture


POSTGRES_CAPACITY_COLLECTION_SUCCESS_METRIC = "lotus_idea_postgres_capacity_collection_success"
POSTGRES_CONNECTION_UTILIZATION_METRIC = "lotus_idea_postgres_connection_utilization_ratio"
POSTGRES_CAPACITY_POSTURE_METRIC = "lotus_idea_postgres_capacity_posture"
POSTGRES_CAPACITY_POSTURES = tuple(posture.value for posture in CapacityPosture)

PostgresCapacityProvider = Callable[[], PostgresCapacityPosture]


class PostgresCapacityCollector:
    def __init__(self, provider: PostgresCapacityProvider | None = None) -> None:
        self._provider = provider
        self._provider_lock = Lock()

    def set_provider(self, provider: PostgresCapacityProvider) -> None:
        with self._provider_lock:
            self._provider = provider

    def collect(self) -> Iterable[Metric]:
        with self._provider_lock:
            provider = self._provider
        try:
            snapshot = provider() if provider is not None else None
        except Exception:
            snapshot = None

        collection_succeeded = snapshot is not None and snapshot.collection_succeeded
        collection = GaugeMetricFamily(
            POSTGRES_CAPACITY_COLLECTION_SUCCESS_METRIC,
            "Whether PostgreSQL capacity posture was collected successfully.",
            labels=["repository"],
        )
        collection.add_metric(["lotus-idea"], 1.0 if collection_succeeded else 0.0)
        yield collection

        posture = snapshot.posture if snapshot is not None else CapacityPosture.UNAVAILABLE
        posture_metric = GaugeMetricFamily(
            POSTGRES_CAPACITY_POSTURE_METRIC,
            "Current bounded PostgreSQL capacity posture.",
            labels=["repository", "posture"],
        )
        for candidate in POSTGRES_CAPACITY_POSTURES:
            posture_metric.add_metric(
                ["lotus-idea", candidate],
                1.0 if candidate == posture.value else 0.0,
            )
        yield posture_metric

        if snapshot is None or snapshot.connection_utilization_fraction is None:
            return
        utilization = GaugeMetricFamily(
            POSTGRES_CONNECTION_UTILIZATION_METRIC,
            "Observed PostgreSQL connections divided by configured maximum connections.",
            labels=["repository"],
        )
        utilization.add_metric(
            ["lotus-idea"],
            snapshot.connection_utilization_fraction,
        )
        yield utilization


_POSTGRES_CAPACITY_COLLECTOR = PostgresCapacityCollector()
_POSTGRES_CAPACITY_REGISTRATION_LOCK = Lock()
_POSTGRES_CAPACITY_REGISTERED = False


def configure_postgres_capacity_metrics(
    provider: PostgresCapacityProvider,
    *,
    registry: CollectorRegistry = REGISTRY,
) -> None:
    global _POSTGRES_CAPACITY_REGISTERED
    _POSTGRES_CAPACITY_COLLECTOR.set_provider(provider)
    with _POSTGRES_CAPACITY_REGISTRATION_LOCK:
        if not _POSTGRES_CAPACITY_REGISTERED:
            registry.register(_POSTGRES_CAPACITY_COLLECTOR)
            _POSTGRES_CAPACITY_REGISTERED = True
