from __future__ import annotations

from datetime import UTC, datetime, timedelta
from collections.abc import Iterator
from typing import Any
from types import SimpleNamespace

import pytest
from tests.support.http import managed_test_client

import app.api.outbox.delivery as outbox_delivery_readiness_api
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, TRUSTED_CALLER_CONTEXT_TOKEN_ENV
from app.application.outbox.readiness import OUTBOX_BROKER_URL_ENV
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventRecord,
    OutboxEventStatus,
    build_candidate_outbox_event,
    mark_outbox_event_failed,
)
from app.main import app
from app.ports.outbox.publisher import OutboxPublishOutcome
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.settings import RUNTIME_PROFILE_ENV


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


def outbox_delivery_run_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.outbox-delivery.run",
    idempotency_key: str = "outbox-run:api:001",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-outbox-delivery-run-api",
        "Idempotency-Key": idempotency_key,
    }


def test_outbox_delivery_readiness_api_returns_source_safe_blocked_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)
    reset_idea_repository_for_tests(
        repository=repository_with_events(
            pending_event("idea.candidate.persisted.v1"),
            failed_event("idea.lifecycle.transitioned.v1"),
            deferred_failed_event("idea.feedback.recorded.v1"),
        )
    )
    client = managed_test_client(app)

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
    assert payload["retryDeferredCount"] == 1
    assert payload["expiredLeaseCount"] == 0
    assert payload["statusCounts"] == {
        "pendingCount": 1,
        "leasedCount": 0,
        "failedCount": 2,
        "publishedCount": 0,
        "deadLetterCount": 0,
        "totalCount": 3,
    }
    assert payload["configurationBlockers"] == ["outbox_broker_not_configured"]
    assert "external_broker_runtime_proof_missing" in payload["certificationBlockers"]
    assert "downstream_consumer_runtime_proof_missing" in payload["certificationBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "idea_high_cash_001" not in response.text
    assert "eventId" not in response.text
    assert "idea.candidate.persisted.v1:idempotency" not in response.text
    assert "broker.example" not in response.text


def test_outbox_delivery_readiness_api_requires_operator_permission() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

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
    client = managed_test_client(app)

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


def test_outbox_delivery_run_once_api_blocks_without_broker_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "blocked"
    assert payload["operatorRunReference"].startswith("outbox-run-")
    assert payload["attemptedCount"] == 0
    assert payload["publishedCount"] == 0
    assert payload["externalBrokerConfigured"] is False
    assert "outbox_broker_not_configured" in payload["certificationBlockers"]
    assert "eventId" not in response.text
    assert "idea_high_cash_001" not in response.text
    assert "idea.candidate.persisted.v1:idempotency" not in response.text
    assert "outbox-run:api:001" not in response.text
    assert (
        resettable_repository_snapshot().outbox_events[event.event_id].status
        is OutboxEventStatus.PENDING
    )


def test_outbox_delivery_run_once_api_blocks_when_durable_repository_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    monkeypatch.setenv(OUTBOX_BROKER_URL_ENV, "https://broker.example.invalid")
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers={
            **outbox_delivery_run_headers(),
            TRUSTED_CALLER_CONTEXT_HEADER: "gateway-secret",
        },
    )

    assert response.status_code == 503
    assert response.json()["code"] == "durable_repository_not_configured"
    assert (
        resettable_repository_snapshot().outbox_events[event.event_id].status
        is OutboxEventStatus.PENDING
    )


def test_outbox_delivery_run_once_api_blocks_invalid_broker_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(OUTBOX_BROKER_URL_ENV, "not-a-url")
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "blocked"
    assert payload["operatorRunReference"].startswith("outbox-run-")
    assert payload["attemptedCount"] == 0
    assert payload["publishedCount"] == 0
    assert payload["externalBrokerConfigured"] is False
    assert "outbox_broker_configuration_invalid" in payload["certificationBlockers"]
    assert (
        resettable_repository_snapshot().outbox_events[event.event_id].status
        is OutboxEventStatus.PENDING
    )


def test_outbox_delivery_run_once_api_publishes_with_configured_publisher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations: list[dict[str, Any]] = []
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "observe_workflow_run",
        lambda **values: observations.append(values),
    )
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    publisher = AcceptingPublisher()
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: publisher,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"deliveredAtUtc": "2026-06-21T10:05:00Z", "limit": 10},
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "completed"
    assert payload["operatorRunReference"].startswith("outbox-run-")
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["attemptedCount"] == 1
    assert payload["publishedCount"] == 1
    assert payload["failedCount"] == 0
    assert payload["deadLetteredCount"] == 0
    assert payload["skippedCount"] == 0
    assert payload["externalBrokerConfigured"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert "external_broker_runtime_proof_missing" in payload["certificationBlockers"]
    assert len(publisher.events) == 1
    assert publisher.events[0].event_id == event.event_id
    assert publisher.events[0].status is OutboxEventStatus.LEASED
    assert publisher.close_count == 1
    assert (
        resettable_repository_snapshot().outbox_events[event.event_id].status
        is OutboxEventStatus.PUBLISHED
    )
    assert "eventId" not in response.text
    assert "idea_high_cash_001" not in response.text
    assert "outbox-run:api:001" not in response.text
    assert len(observations) == 1
    assert observations[0]["workflow"] == "outbox_delivery"
    assert observations[0]["outcome"] == "accepted"
    assert observations[0]["item_count"] == 1
    assert observations[0]["duration_seconds"] >= 0


def test_outbox_delivery_run_once_api_requires_operator_permission() -> None:
    client = managed_test_client(app)

    response = client.post("/api/v1/outbox-delivery/run-once")
    role_denied = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(roles="advisor"),
    )
    capability_denied = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(
            capabilities="idea.outbox-delivery.readiness.read",
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_outbox_delivery_run_once_api_requires_idempotency_key() -> None:
    client = managed_test_client(app)
    headers = outbox_delivery_run_headers()
    headers.pop("Idempotency-Key")

    response = client.post("/api/v1/outbox-delivery/run-once", headers=headers)
    blank = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers={**headers, "Idempotency-Key": " "},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "idempotency key is required" in response.text
    assert blank.status_code == 400
    assert blank.json()["code"] == "invalid_request"


def test_outbox_delivery_run_once_api_rejects_non_utc_delivery_time() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"deliveredAtUtc": "2026-06-21T18:05:00+08:00"},
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_outbox_delivery_run_once_api_rejects_limit_above_capacity_ceiling() -> None:
    response = managed_test_client(app).post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 101},
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_outbox_delivery_run_once_api_sheds_before_publisher_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "evaluate_nonessential_workload_capacity",
        lambda repository: SimpleNamespace(
            allowed=False,
            blocker="postgres_capacity_shed_active",
        ),
    )
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: pytest.fail("shed workflow must not construct publisher"),
    )

    response = managed_test_client(app).post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(idempotency_key="capacity-shed:001"),
    )

    assert response.status_code == 200
    assert response.json()["runStatus"] == "blocked"
    assert "postgres_capacity_shed_active" in response.json()["certificationBlockers"]
    assert response.json()["attemptedCount"] == 0


def test_outbox_delivery_run_once_api_replays_same_operator_run_without_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(first_event))
    publisher = AcceptingPublisher()
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: publisher,
    )
    client = managed_test_client(app)
    headers = outbox_delivery_run_headers(idempotency_key="outbox-run:api-replay:001")

    first = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 10},
        headers=headers,
    )
    replay = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 10},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["runStatus"] == "completed"
    assert first.json()["publishedCount"] == 1
    assert replay.status_code == 200
    assert replay.json()["runStatus"] == "replayed"
    assert replay.json()["attemptedCount"] == 0
    assert replay.json()["operatorRunReference"] == first.json()["operatorRunReference"]
    assert len(publisher.events) == 1
    assert publisher.close_count == 2
    assert "outbox-run:api-replay:001" not in replay.text


def test_outbox_delivery_run_once_api_preserves_results_when_publisher_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    publisher = AcceptingPublisher(
        close_error=RuntimeError("raw broker close failure idea_high_cash_001")
    )
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: publisher,
    )
    events: list[tuple[str, str, str | None, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.error_code,
                dict(event.attributes),
            )
        )

    monkeypatch.setattr(outbox_delivery_readiness_api, "emit_operation_event", capture)
    client = managed_test_client(app)
    headers = outbox_delivery_run_headers(idempotency_key="outbox-run:close-failure:001")

    completed = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 10},
        headers=headers,
    )
    replayed = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 10},
        headers=headers,
    )
    conflict = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 20},
        headers=headers,
    )

    assert completed.status_code == 200
    assert completed.json()["runStatus"] == "completed"
    assert replayed.status_code == 200
    assert replayed.json()["runStatus"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert publisher.close_count == 3
    assert len(publisher.events) == 1
    assert "raw broker close failure" not in completed.text
    assert "raw broker close failure" not in replayed.text
    assert "raw broker close failure" not in conflict.text
    cleanup_events = [
        event
        for event in events
        if event[1] == "suppressed" and event[2] == "publisher_cleanup_failed"
    ]
    assert len(cleanup_events) == 3
    assert all(event[3]["cleanup_phase"] == "publisher_close" for event in cleanup_events)
    assert [event[1] for event in events if event[1] != "suppressed"] == [
        "accepted",
        "replayed",
        "conflict",
    ]


def test_outbox_delivery_run_once_api_conflicts_same_operator_run_with_different_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    publisher = AcceptingPublisher()
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: publisher,
    )
    client = managed_test_client(app)
    headers = outbox_delivery_run_headers(idempotency_key="outbox-run:api-conflict:001")

    first = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 10},
        headers=headers,
    )
    conflict = client.post(
        "/api/v1/outbox-delivery/run-once",
        params={"limit": 20},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["publishedCount"] == 1
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert len(publisher.events) == 1
    assert publisher.close_count == 2
    assert "outbox-run:api-conflict:001" not in conflict.text


def test_outbox_delivery_run_once_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = pending_event("idea.candidate.persisted.v1")
    reset_idea_repository_for_tests(repository=repository_with_events(event))
    publisher = AcceptingPublisher()
    monkeypatch.setattr(
        outbox_delivery_readiness_api,
        "_build_outbox_publisher_from_environment",
        lambda: publisher,
    )
    events: list[tuple[str, str, str, bool, bool, str | None, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
                dict(event.attributes),
            )
        )

    monkeypatch.setattr(outbox_delivery_readiness_api, "emit_operation_event", capture)
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/outbox-delivery/run-once",
        headers=outbox_delivery_run_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "outbox_delivery_run_once",
            "accepted",
            "not_certified",
            False,
            False,
            None,
            {
                "attempted_count_bucket": "1-10",
                "operator_run_reference": response.json()["operatorRunReference"],
            },
        )
    ]


class AcceptingPublisher:
    def __init__(self, close_error: Exception | None = None) -> None:
        self.events: list[OutboxEventRecord] = []
        self.close_count = 0
        self.close_error = close_error

    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        self.events.append(event)
        return OutboxPublishOutcome.accepted_by_publisher()

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


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
        failed_at_utc=EVENT_TIME,
        max_retry_count=3,
        next_attempt_at_utc=EVENT_TIME + timedelta(days=30),
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


def deferred_failed_event(event_type: str) -> OutboxEventRecord:
    return mark_outbox_event_failed(
        pending_event(event_type),
        failure_reason="publisher_rejected",
        failed_at_utc=EVENT_TIME,
        max_retry_count=3,
        next_attempt_at_utc=EVENT_TIME + timedelta(seconds=60),
    )


def resettable_repository_snapshot() -> IdeaRepositorySnapshot:
    repository = get_idea_repository()
    return repository.snapshot()
