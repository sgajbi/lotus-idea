from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.contracts.operational_limits import (
    DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT as DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
)
from app.domain import OutboxEventStatus
from app.ports.idea_repository import (
    CandidateSnapshotRepository,
    OutboxDeliveryReadinessProjectionRepository,
    OutboxDeliveryReadinessRepositorySummary,
    OutboxDeliveryRepository,
)


OUTBOX_BROKER_URL_ENV = "LOTUS_IDEA_OUTBOX_BROKER_URL"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
OUTBOX_EVENT_CONTRACT_PATH = (
    REPOSITORY_ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
)
OUTBOX_CONSUMER_CONTRACT_PATH = (
    REPOSITORY_ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-consumers.v1.json"
)


@dataclass(frozen=True)
class OutboxDeliveryStatusCounts:
    pending_count: int
    leased_count: int
    failed_count: int
    published_count: int
    dead_letter_count: int

    @property
    def total_count(self) -> int:
        return (
            self.pending_count
            + self.leased_count
            + self.failed_count
            + self.published_count
            + self.dead_letter_count
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
    retry_deferred_count: int
    expired_lease_count: int
    oldest_delivery_ready_age_seconds: float
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
    evaluated_at_utc: datetime | None = None,
) -> OutboxDeliveryReadinessSnapshot:
    if max_retry_count <= 0:
        raise ValueError("max_retry_count must be positive")
    evaluated_at = evaluated_at_utc or datetime.now(UTC)
    _require_aware_utc(evaluated_at, "evaluated_at_utc")

    readiness_summary = _readiness_summary(
        repository,
        max_retry_count=max_retry_count,
        evaluated_at_utc=evaluated_at,
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
        delivery_ready_count=readiness_summary.delivery_ready_count,
        retry_deferred_count=readiness_summary.retry_deferred_count,
        expired_lease_count=readiness_summary.expired_lease_count,
        oldest_delivery_ready_age_seconds=_oldest_delivery_ready_age_seconds(
            readiness_summary.oldest_delivery_ready_at_utc,
            evaluated_at_utc=evaluated_at,
        ),
        max_retry_count=max_retry_count,
        status_counts=_status_counts_from_summary(readiness_summary),
        source_of_truth={
            "outbox_delivery": "src/app/application/outbox/delivery.py",
            "outbox_readiness": "src/app/application/outbox/readiness.py",
            "publisher_port": "src/app/ports/outbox/publisher.py",
            "publisher_adapter": "src/app/infrastructure/outbox/publisher.py",
            "outbox_broker_runtime_execution": (
                "src/app/application/outbox/broker/runtime_execution.py"
            ),
            "outbox_broker_runtime_execution_gate": (
                "make outbox-broker-runtime-execution-proof-gate"
            ),
            "repository_port": "src/app/ports/idea_repository.py",
            "outbox_event_contract": ("contracts/outbox-events/lotus-idea-outbox-events.v1.json"),
            "outbox_event_contract_gate": "make outbox-event-contract-gate",
            "outbox_consumer_contract": (
                "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json"
            ),
            "outbox_consumer_contract_gate": "make outbox-consumer-contract-gate",
            "rfc_slice_06": (
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                "RFC-0002-slice-06-persistence-replay-idempotency-and-audit.md"
            ),
        },
        configuration_blockers=configuration_blockers,
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


def _readiness_summary(
    repository: OutboxDeliveryRepository,
    *,
    max_retry_count: int,
    evaluated_at_utc: datetime,
) -> OutboxDeliveryReadinessRepositorySummary:
    if isinstance(repository, OutboxDeliveryReadinessProjectionRepository):
        return repository.outbox_delivery_readiness_summary(
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc,
        )
    status_counts, expired_lease_count, retry_deferred_count = _snapshot_status_counts(
        repository,
        evaluated_at_utc=evaluated_at_utc,
        max_retry_count=max_retry_count,
    )
    delivery_ready_count = len(
        repository.outbox_events_for_delivery(
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc,
        )
    )
    oldest_delivery_ready_at_utc = _oldest_delivery_ready_at_utc(
        repository,
        evaluated_at_utc=evaluated_at_utc,
        max_retry_count=max_retry_count,
    )
    return OutboxDeliveryReadinessRepositorySummary(
        pending_count=status_counts.pending_count,
        leased_count=status_counts.leased_count,
        failed_count=status_counts.failed_count,
        published_count=status_counts.published_count,
        dead_letter_count=status_counts.dead_letter_count,
        expired_lease_count=expired_lease_count,
        delivery_ready_count=delivery_ready_count,
        retry_deferred_count=retry_deferred_count,
        oldest_delivery_ready_at_utc=oldest_delivery_ready_at_utc,
    )


def _oldest_delivery_ready_at_utc(
    repository: CandidateSnapshotRepository,
    *,
    evaluated_at_utc: datetime,
    max_retry_count: int,
) -> datetime | None:
    ready_at_values: list[datetime] = []
    for event in repository.snapshot().outbox_events.values():
        if event.status is OutboxEventStatus.PENDING:
            ready_at_values.append(event.occurred_at_utc)
        elif (
            event.status is OutboxEventStatus.FAILED
            and event.retry_count < max_retry_count
            and event.next_attempt_at_utc is not None
            and event.next_attempt_at_utc <= evaluated_at_utc
        ):
            ready_at_values.append(event.next_attempt_at_utc)
        elif (
            event.status is OutboxEventStatus.LEASED
            and event.lease_expires_at_utc is not None
            and event.lease_expires_at_utc <= evaluated_at_utc
        ):
            ready_at_values.append(event.lease_expires_at_utc)
    return min(ready_at_values, default=None)


def _oldest_delivery_ready_age_seconds(
    oldest_delivery_ready_at_utc: datetime | None,
    *,
    evaluated_at_utc: datetime,
) -> float:
    if oldest_delivery_ready_at_utc is None:
        return 0.0
    _require_aware_utc(oldest_delivery_ready_at_utc, "oldest_delivery_ready_at_utc")
    return max(0.0, (evaluated_at_utc - oldest_delivery_ready_at_utc).total_seconds())


def _snapshot_status_counts(
    repository: CandidateSnapshotRepository,
    *,
    evaluated_at_utc: datetime,
    max_retry_count: int,
) -> tuple[OutboxDeliveryStatusCounts, int, int]:
    counts = {
        OutboxEventStatus.PENDING: 0,
        OutboxEventStatus.LEASED: 0,
        OutboxEventStatus.FAILED: 0,
        OutboxEventStatus.PUBLISHED: 0,
        OutboxEventStatus.DEAD_LETTER: 0,
    }
    expired_lease_count = 0
    retry_deferred_count = 0
    for event in repository.snapshot().outbox_events.values():
        counts[event.status] += 1
        if (
            event.status is OutboxEventStatus.LEASED
            and event.lease_expires_at_utc is not None
            and event.lease_expires_at_utc <= evaluated_at_utc
        ):
            expired_lease_count += 1
        if (
            event.status is OutboxEventStatus.FAILED
            and event.retry_count < max_retry_count
            and event.next_attempt_at_utc is not None
            and event.next_attempt_at_utc > evaluated_at_utc
        ):
            retry_deferred_count += 1
    return (
        OutboxDeliveryStatusCounts(
            pending_count=counts[OutboxEventStatus.PENDING],
            leased_count=counts[OutboxEventStatus.LEASED],
            failed_count=counts[OutboxEventStatus.FAILED],
            published_count=counts[OutboxEventStatus.PUBLISHED],
            dead_letter_count=counts[OutboxEventStatus.DEAD_LETTER],
        ),
        expired_lease_count,
        retry_deferred_count,
    )


def _status_counts_from_summary(
    summary: OutboxDeliveryReadinessRepositorySummary,
) -> OutboxDeliveryStatusCounts:
    return OutboxDeliveryStatusCounts(
        pending_count=summary.pending_count,
        leased_count=summary.leased_count,
        failed_count=summary.failed_count,
        published_count=summary.published_count,
        dead_letter_count=summary.dead_letter_count,
    )


def _configuration_blockers() -> tuple[str, ...]:
    if os.getenv(OUTBOX_BROKER_URL_ENV, "").strip():
        return ()
    return ("outbox_broker_not_configured",)


def outbox_delivery_certification_blockers() -> tuple[str, ...]:
    return (
        "external_broker_runtime_proof_missing",
        _downstream_consumer_certification_blocker(),
        _platform_mesh_event_certification_blocker(),
        "gateway_workbench_proof_missing",
        "supported_feature_promotion_missing",
    )


def _downstream_consumer_certification_blocker() -> str:
    if OUTBOX_CONSUMER_CONTRACT_PATH.is_file():
        return "downstream_consumer_runtime_proof_missing"
    return "downstream_consumer_contracts_missing"


def _platform_mesh_event_certification_blocker() -> str:
    if OUTBOX_EVENT_CONTRACT_PATH.is_file():
        return "platform_mesh_event_publication_proof_missing"
    return "platform_mesh_event_contract_missing"


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
