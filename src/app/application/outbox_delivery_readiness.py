from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.domain import OutboxEventStatus
from app.ports.idea_repository import CandidateSnapshotRepository, OutboxDeliveryRepository


OUTBOX_BROKER_URL_ENV = "LOTUS_IDEA_OUTBOX_BROKER_URL"
DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT = 3
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OUTBOX_EVENT_CONTRACT_PATH = (
    REPOSITORY_ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
)


@dataclass(frozen=True)
class OutboxDeliveryStatusCounts:
    pending_count: int
    failed_count: int
    published_count: int
    dead_letter_count: int

    @property
    def total_count(self) -> int:
        return (
            self.pending_count + self.failed_count + self.published_count + self.dead_letter_count
        )


@dataclass(frozen=True)
class OutboxDeliveryReadinessSnapshot:
    repository: str
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    durable_storage_backed: bool
    external_broker_configured: bool
    external_broker_publisher_adapter_present: bool
    delivery_ready_count: int
    max_retry_count: int
    status_counts: OutboxDeliveryStatusCounts
    source_of_truth: Mapping[str, str]
    configuration_blockers: tuple[str, ...]
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_of_truth",
            MappingProxyType(dict(self.source_of_truth)),
        )
        object.__setattr__(self, "configuration_blockers", tuple(self.configuration_blockers))
        object.__setattr__(self, "certification_blockers", tuple(self.certification_blockers))


def build_outbox_delivery_readiness_snapshot(
    *,
    repository: OutboxDeliveryRepository,
    durable_storage_backed: bool,
    max_retry_count: int = DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
) -> OutboxDeliveryReadinessSnapshot:
    if max_retry_count <= 0:
        raise ValueError("max_retry_count must be positive")

    status_counts = _status_counts(repository)
    delivery_ready_count = len(
        repository.outbox_events_for_delivery(max_retry_count=max_retry_count)
    )
    configuration_blockers = _configuration_blockers()
    certification_blockers = outbox_delivery_certification_blockers()
    certification_ready = not configuration_blockers and not certification_blockers

    return OutboxDeliveryReadinessSnapshot(
        repository="lotus-idea",
        readiness_status=("ready" if certification_ready else "blocked"),
        supportability_status="not_certified",
        certification_ready=certification_ready,
        durable_storage_backed=durable_storage_backed,
        external_broker_configured=bool(os.getenv(OUTBOX_BROKER_URL_ENV, "").strip()),
        external_broker_publisher_adapter_present=True,
        delivery_ready_count=delivery_ready_count,
        max_retry_count=max_retry_count,
        status_counts=status_counts,
        source_of_truth={
            "outbox_delivery": "src/app/application/outbox_delivery.py",
            "outbox_readiness": "src/app/application/outbox_delivery_readiness.py",
            "publisher_port": "src/app/ports/outbox_publisher.py",
            "publisher_adapter": "src/app/infrastructure/outbox_publisher.py",
            "repository_port": "src/app/ports/idea_repository.py",
            "outbox_event_contract": ("contracts/outbox-events/lotus-idea-outbox-events.v1.json"),
            "outbox_event_contract_gate": "make outbox-event-contract-gate",
            "rfc_slice_06": (
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                "RFC-0002-slice-06-persistence-replay-idempotency-and-audit.md"
            ),
        },
        configuration_blockers=configuration_blockers,
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


def _status_counts(
    repository: CandidateSnapshotRepository,
) -> OutboxDeliveryStatusCounts:
    counts = {
        OutboxEventStatus.PENDING: 0,
        OutboxEventStatus.FAILED: 0,
        OutboxEventStatus.PUBLISHED: 0,
        OutboxEventStatus.DEAD_LETTER: 0,
    }
    for event in repository.snapshot().outbox_events.values():
        counts[event.status] += 1
    return OutboxDeliveryStatusCounts(
        pending_count=counts[OutboxEventStatus.PENDING],
        failed_count=counts[OutboxEventStatus.FAILED],
        published_count=counts[OutboxEventStatus.PUBLISHED],
        dead_letter_count=counts[OutboxEventStatus.DEAD_LETTER],
    )


def _configuration_blockers() -> tuple[str, ...]:
    if os.getenv(OUTBOX_BROKER_URL_ENV, "").strip():
        return ()
    return ("outbox_broker_not_configured",)


def outbox_delivery_certification_blockers() -> tuple[str, ...]:
    return (
        "external_broker_runtime_proof_missing",
        "downstream_consumer_contracts_missing",
        _platform_mesh_event_certification_blocker(),
        "gateway_workbench_proof_missing",
        "supported_feature_promotion_missing",
    )


def _platform_mesh_event_certification_blocker() -> str:
    if OUTBOX_EVENT_CONTRACT_PATH.is_file():
        return "platform_mesh_event_publication_proof_missing"
    return "platform_mesh_event_contract_missing"
