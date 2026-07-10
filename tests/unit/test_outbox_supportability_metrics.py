from __future__ import annotations

from prometheus_client import CollectorRegistry, generate_latest
from fastapi.testclient import TestClient

import app.main as main_module
from app.application.outbox_delivery_readiness import build_outbox_delivery_readiness_snapshot
from app.observability.outbox_supportability import (
    OUTBOX_DELIVERY_STATES,
    OutboxDeliverySupportabilityCollector,
)
from tests.unit.test_outbox_delivery_readiness import (
    PUBLISHED_AT,
    dead_letter_event,
    deferred_failed_event,
    expired_lease_event,
    failed_event,
    pending_event,
    published_event,
    repository_with_events,
)


def test_outbox_supportability_collector_exposes_bounded_runtime_posture(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LOTUS_IDEA_OUTBOX_BROKER_URL", raising=False)
    repository = repository_with_events(
        pending_event("idea.candidate.persisted.v1"),
        expired_lease_event("idea.lifecycle.transitioned.v1"),
        failed_event("idea.feedback.recorded.v1"),
        deferred_failed_event("idea.review.decision_recorded.v1"),
        published_event("idea.conversion.intent_requested.v1"),
        dead_letter_event("idea.report_evidence_pack.requested.v1"),
    )
    collector = OutboxDeliverySupportabilityCollector(
        lambda: build_outbox_delivery_readiness_snapshot(
            repository=repository,
            durable_storage_backed=True,
            evaluated_at_utc=PUBLISHED_AT,
        )
    )
    registry = CollectorRegistry()
    registry.register(collector)

    metrics = generate_latest(registry).decode("utf-8")

    assert 'lotus_idea_outbox_delivery_collection_success{repository="lotus-idea"} 1.0' in metrics
    assert (
        'lotus_idea_outbox_delivery_events{repository="lotus-idea",state="dead_letter"} 1.0'
        in metrics
    )
    assert (
        'lotus_idea_outbox_delivery_events{repository="lotus-idea",state="delivery_ready"} 3.0'
        in metrics
    )
    assert (
        'lotus_idea_outbox_delivery_events{repository="lotus-idea",state="retry_deferred"} 1.0'
        in metrics
    )
    assert (
        'lotus_idea_outbox_delivery_events{repository="lotus-idea",state="expired_lease"} 1.0'
        in metrics
    )
    assert (
        'lotus_idea_outbox_delivery_oldest_ready_age_seconds{repository="lotus-idea"} 300.0'
        in metrics
    )
    assert 'lotus_idea_outbox_delivery_configuration_ready{repository="lotus-idea"} 0.0' in metrics
    assert set(OUTBOX_DELIVERY_STATES) == {
        "pending",
        "leased",
        "failed",
        "published",
        "dead_letter",
        "delivery_ready",
        "retry_deferred",
        "expired_lease",
    }
    for forbidden in ("event_id", "candidate_id", "portfolio_id", "client_id", "payload"):
        assert forbidden not in metrics


def test_outbox_supportability_collector_fails_closed_without_scrape_failure() -> None:
    def unavailable_projection():
        raise RuntimeError("database unavailable")

    registry = CollectorRegistry()
    registry.register(OutboxDeliverySupportabilityCollector(unavailable_projection))

    metrics = generate_latest(registry).decode("utf-8")

    assert 'lotus_idea_outbox_delivery_collection_success{repository="lotus-idea"} 0.0' in metrics
    assert "lotus_idea_outbox_delivery_events" not in metrics
    assert "database unavailable" not in metrics


def test_metrics_endpoint_collects_posture_without_readiness_api_call(monkeypatch) -> None:
    repository = repository_with_events(
        pending_event("idea.candidate.persisted.v1"),
        dead_letter_event("idea.report_evidence_pack.requested.v1"),
    )
    monkeypatch.setattr(main_module, "get_idea_repository", lambda: repository)
    monkeypatch.setattr(main_module, "idea_repository_durable_storage_backed", lambda: True)

    with TestClient(main_module.create_app()) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert (
        'lotus_idea_outbox_delivery_events{repository="lotus-idea",state="dead_letter"} 1.0'
        in response.text
    )
    assert (
        'lotus_idea_outbox_delivery_collection_success{repository="lotus-idea"} 1.0'
        in response.text
    )
