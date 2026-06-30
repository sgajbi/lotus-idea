from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.outbox_delivery_readiness import (
    DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
    OUTBOX_BROKER_URL_ENV,
    build_outbox_delivery_readiness_snapshot,
)
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventRecord,
    build_candidate_outbox_event,
    lease_outbox_event,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 6, 21, 10, 5, tzinfo=UTC)


def test_outbox_delivery_readiness_reports_blocked_foundation_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)
    repository = repository_with_events(
        pending_event("idea.candidate.persisted.v1"),
        leased_event("idea.lifecycle.transitioned.v1"),
        expired_lease_event("idea.conversion.intent_requested.v1"),
        failed_event("idea.conversion.outcome_recorded.v1"),
        published_event("idea.review.decision_recorded.v1"),
        dead_letter_event("idea.report_evidence_pack.requested.v1"),
    )

    snapshot = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=False,
        evaluated_at_utc=PUBLISHED_AT,
    )

    assert snapshot.repository == "lotus-idea"
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.durable_storage_backed is False
    assert snapshot.external_broker_configured is False
    assert snapshot.external_broker_publisher_adapter_present is True
    assert snapshot.delivery_ready_count == 3
    assert snapshot.expired_lease_count == 1
    assert snapshot.max_retry_count == DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT
    assert snapshot.status_counts.pending_count == 1
    assert snapshot.status_counts.leased_count == 2
    assert snapshot.status_counts.failed_count == 1
    assert snapshot.status_counts.published_count == 1
    assert snapshot.status_counts.dead_letter_count == 1
    assert snapshot.status_counts.total_count == 6
    assert snapshot.configuration_blockers == ("outbox_broker_not_configured",)
    assert "external_broker_runtime_proof_missing" in snapshot.certification_blockers
    assert (
        snapshot.source_of_truth["outbox_event_contract"]
        == "contracts/outbox-events/lotus-idea-outbox-events.v1.json"
    )
    assert snapshot.source_of_truth["outbox_event_contract_gate"] == (
        "make outbox-event-contract-gate"
    )
    assert snapshot.source_of_truth["outbox_consumer_contract"] == (
        "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json"
    )
    assert snapshot.source_of_truth["outbox_consumer_contract_gate"] == (
        "make outbox-consumer-contract-gate"
    )
    assert snapshot.supported_feature_promoted is False


def test_outbox_delivery_readiness_keeps_certification_blocked_with_broker_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(OUTBOX_BROKER_URL_ENV, "https://broker.example.invalid")
    repository = repository_with_events(pending_event("idea.candidate.persisted.v1"))

    snapshot = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=True,
    )

    assert snapshot.external_broker_configured is True
    assert snapshot.external_broker_publisher_adapter_present is True
    assert snapshot.durable_storage_backed is True
    assert snapshot.configuration_blockers == ()
    assert snapshot.certification_ready is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.certification_blockers == (
        "external_broker_runtime_proof_missing",
        "downstream_consumer_runtime_proof_missing",
        "platform_mesh_event_publication_proof_missing",
        "gateway_workbench_proof_missing",
        "supported_feature_promotion_missing",
    )


def test_outbox_delivery_readiness_rejects_invalid_retry_limit() -> None:
    with pytest.raises(ValueError, match="max_retry_count must be positive"):
        build_outbox_delivery_readiness_snapshot(
            repository=repository_with_events(),
            durable_storage_backed=False,
            max_retry_count=0,
        )


def pending_event(event_type: str) -> OutboxEventRecord:
    return build_candidate_outbox_event(
        event_type=event_type,
        aggregate_id="idea_high_cash_001",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
        idempotency_key=f"{event_type}:idempotency",
    )


def failed_event(event_type: str) -> OutboxEventRecord:
    return mark_outbox_event_failed(
        pending_event(event_type),
        failure_reason="publisher_rejected",
        max_retry_count=DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
    )


def published_event(event_type: str) -> OutboxEventRecord:
    return mark_outbox_event_published(
        pending_event(event_type),
        published_at_utc=PUBLISHED_AT,
    )


def leased_event(event_type: str) -> OutboxEventRecord:
    return lease_outbox_event(
        pending_event(event_type),
        lease_owner="worker-1",
        lease_attempt_id=f"{event_type}:lease",
        lease_expires_at_utc=PUBLISHED_AT + timedelta(minutes=5),
    )


def expired_lease_event(event_type: str) -> OutboxEventRecord:
    return lease_outbox_event(
        pending_event(event_type),
        lease_owner="worker-2",
        lease_attempt_id=f"{event_type}:lease",
        lease_expires_at_utc=PUBLISHED_AT - timedelta(minutes=1),
    )


def dead_letter_event(event_type: str) -> OutboxEventRecord:
    return mark_outbox_event_failed(
        pending_event(event_type),
        failure_reason="publisher_rejected",
        max_retry_count=1,
    )


def repository_with_events(*events: OutboxEventRecord) -> InMemoryIdeaRepository:
    return InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            outbox_events={event.event_id: event for event in events},
        )
    )
