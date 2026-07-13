from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import Lock

from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_client.core import GaugeMetricFamily, Metric

from app.application.outbox.readiness import OutboxDeliveryReadinessSnapshot

OUTBOX_DELIVERY_STATE_METRIC = "lotus_idea_outbox_delivery_events"
OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC = "lotus_idea_outbox_delivery_oldest_ready_age_seconds"
OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC = "lotus_idea_outbox_delivery_configuration_ready"
OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC = "lotus_idea_outbox_delivery_collection_success"
OUTBOX_DELIVERY_STATES = (
    "pending",
    "leased",
    "failed",
    "published",
    "dead_letter",
    "delivery_ready",
    "retry_deferred",
    "expired_lease",
)

OutboxReadinessProvider = Callable[[], OutboxDeliveryReadinessSnapshot]


class OutboxDeliverySupportabilityCollector:
    def __init__(self, provider: OutboxReadinessProvider | None = None) -> None:
        self._provider = provider
        self._provider_lock = Lock()

    def set_provider(self, provider: OutboxReadinessProvider) -> None:
        with self._provider_lock:
            self._provider = provider

    def collect(self) -> Iterable[Metric]:
        with self._provider_lock:
            provider = self._provider
        try:
            snapshot = provider() if provider is not None else None
        except Exception:
            snapshot = None

        collection = GaugeMetricFamily(
            OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC,
            "Whether the bounded outbox supportability projection was collected successfully.",
            labels=["repository"],
        )
        collection.add_metric(["lotus-idea"], 1.0 if snapshot is not None else 0.0)
        yield collection
        if snapshot is None:
            return

        counts = snapshot.status_counts
        state_values = {
            "pending": counts.pending_count,
            "leased": counts.leased_count,
            "failed": counts.failed_count,
            "published": counts.published_count,
            "dead_letter": counts.dead_letter_count,
            "delivery_ready": snapshot.delivery_ready_count,
            "retry_deferred": snapshot.retry_deferred_count,
            "expired_lease": snapshot.expired_lease_count,
        }
        state_metric = GaugeMetricFamily(
            OUTBOX_DELIVERY_STATE_METRIC,
            "Current bounded outbox event counts by governed delivery state.",
            labels=["repository", "state"],
        )
        for state in OUTBOX_DELIVERY_STATES:
            state_metric.add_metric([snapshot.repository, state], state_values[state])
        yield state_metric

        age_metric = GaugeMetricFamily(
            OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC,
            "Age in seconds of the oldest event currently eligible for delivery.",
            labels=["repository"],
        )
        age_metric.add_metric([snapshot.repository], snapshot.oldest_delivery_ready_age_seconds)
        yield age_metric

        configuration_metric = GaugeMetricFamily(
            OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC,
            "Whether the local outbox delivery configuration has no blockers.",
            labels=["repository"],
        )
        configuration_metric.add_metric(
            [snapshot.repository], 0.0 if snapshot.configuration_blockers else 1.0
        )
        yield configuration_metric


_OUTBOX_SUPPORTABILITY_COLLECTOR = OutboxDeliverySupportabilityCollector()
_OUTBOX_SUPPORTABILITY_REGISTRATION_LOCK = Lock()
_OUTBOX_SUPPORTABILITY_REGISTERED = False


def configure_outbox_supportability_metrics(
    provider: OutboxReadinessProvider,
    *,
    registry: CollectorRegistry = REGISTRY,
) -> None:
    global _OUTBOX_SUPPORTABILITY_REGISTERED
    _OUTBOX_SUPPORTABILITY_COLLECTOR.set_provider(provider)
    with _OUTBOX_SUPPORTABILITY_REGISTRATION_LOCK:
        if not _OUTBOX_SUPPORTABILITY_REGISTERED:
            registry.register(_OUTBOX_SUPPORTABILITY_COLLECTOR)
            _OUTBOX_SUPPORTABILITY_REGISTERED = True
