from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.outbox_delivery_readiness as outbox_delivery_readiness_api
from app.application.outbox_delivery_readiness import OUTBOX_BROKER_URL_ENV
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventRecord,
    build_candidate_outbox_event,
    mark_outbox_event_failed,
)
from app.main import app
from app.repository_state import reset_idea_repository_for_tests


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_repository_provider() -> Iterator[None]:
    reset_idea_repository_for_tests()
    yield
    reset_idea_repository_for_tests()


def outbox_delivery_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.outbox-delivery.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-outbox-delivery-readiness-api",
    }


def test_outbox_delivery_readiness_api_returns_source_safe_blocked_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)
    reset_idea_repository_for_tests(
        repository=repository_with_events(
            pending_event("idea.candidate.persisted.v1"),
            failed_event("idea.lifecycle.transitioned.v1"),
        )
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/outbox-delivery/readiness",
        headers=outbox_delivery_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["durableStorageBacked"] is False
    assert payload["externalBrokerConfigured"] is False
    assert payload["externalBrokerPublisherAdapterPresent"] is True
    assert payload["deliveryReadyCount"] == 2
    assert payload["statusCounts"] == {
        "pendingCount": 1,
        "failedCount": 1,
        "publishedCount": 0,
        "deadLetterCount": 0,
        "totalCount": 2,
    }
    assert payload["configurationBlockers"] == ["outbox_broker_not_configured"]
    assert "external_broker_runtime_proof_missing" in payload["certificationBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "idea_high_cash_001" not in response.text
    assert "eventId" not in response.text
    assert "idea.candidate.persisted.v1:idempotency" not in response.text
    assert "broker.example" not in response.text


def test_outbox_delivery_readiness_api_requires_operator_permission() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get("/api/v1/outbox-delivery/readiness")
    role_denied = client.get(
        "/api/v1/outbox-delivery/readiness",
        headers=outbox_delivery_readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/outbox-delivery/readiness",
        headers=outbox_delivery_readiness_headers(
            capabilities="idea.downstream-realization.readiness.read",
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"
    assert "outbox_broker_url" not in response.text.lower()


def test_outbox_delivery_readiness_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)
    reset_idea_repository_for_tests(
        repository=repository_with_events(pending_event("idea.candidate.persisted.v1"))
    )
    events: list[tuple[str, str, str, bool, bool, str | None]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(outbox_delivery_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get(
        "/api/v1/outbox-delivery/readiness",
        headers=outbox_delivery_readiness_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "outbox_delivery_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]


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
        max_retry_count=3,
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
