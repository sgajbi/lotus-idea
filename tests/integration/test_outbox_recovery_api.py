from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import app.api.outbox_recovery as recovery_api
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_TOKEN_ENV
from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventStatus,
    build_candidate_outbox_event,
    mark_outbox_event_failed,
)
from app.main import app
from app.ports.outbox_publisher import OutboxPublishOutcome
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.runtime.settings import RUNTIME_PROFILE_ENV


EVENT_TIME = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_repository_provider() -> Iterator[None]:
    reset_idea_repository_for_tests()
    yield
    reset_idea_repository_for_tests()


def test_dead_letter_inspection_is_operator_only_and_source_safe() -> None:
    event = _dead_lettered_event()
    reset_idea_repository_for_tests(repository=_repository_with_event(event))
    client = TestClient(app)

    denied = client.get("/api/v1/outbox-delivery/dead-letters")
    response = client.get(
        "/api/v1/outbox-delivery/dead-letters",
        headers=_headers(capability="idea.outbox-recovery.read"),
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert response.status_code == 200
    payload = response.json()
    assert payload["returnedCount"] == 1
    assert payload["items"][0]["supportReference"].startswith("outbox-dlq-")
    assert payload["items"][0]["eventFamily"] == "idea.candidate.persisted.v1"
    assert payload["items"][0]["failureReason"] == "publisher_rejected"
    assert payload["items"][0]["disposition"] == "quarantined"
    assert event.event_id not in response.text
    assert "candidate-sensitive" not in response.text
    assert "candidate-secret-key" not in response.text
    assert "payload" not in response.text.lower()


def test_dead_letter_redrive_publishes_once_and_replays_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    reset_idea_repository_for_tests(repository=repository)
    publisher = RecordingPublisher(accepted=True)
    monkeypatch.setattr(recovery_api, "build_outbox_publisher_from_environment", lambda: publisher)
    client = TestClient(app)
    support_reference = _support_reference(client)
    headers = _headers(
        capability="idea.outbox-recovery.redrive",
        idempotency_key="outbox-redrive:api:001",
    )

    first = client.post(
        f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive",
        headers=headers,
        json={"reason": "broker_route_corrected", "changeReference": "CHG-2026-0710"},
    )
    replay = client.post(
        f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive",
        headers=headers,
        json={"reason": "broker_route_corrected", "changeReference": "CHG-2026-0710"},
    )

    assert first.status_code == 200
    assert first.json()["runStatus"] == "published"
    assert first.json()["publicationAttempted"] is True
    assert first.json()["recoveryReference"].startswith("recovery_")
    assert replay.status_code == 200
    assert replay.json()["runStatus"] == "replayed"
    assert replay.json()["publicationAttempted"] is False
    assert len(publisher.events) == 1
    assert publisher.close_count == 2
    persisted = repository.snapshot().outbox_events[event.event_id]
    assert persisted.status is OutboxEventStatus.PUBLISHED
    assert persisted.failure_reason == "publisher_rejected"
    assert "outbox-redrive:api:001" not in first.text
    assert "candidate-sensitive" not in first.text


def test_dead_letter_redrive_conflict_and_publisher_failure_remain_quarantined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    reset_idea_repository_for_tests(repository=repository)
    publisher = RecordingPublisher(accepted=False)
    monkeypatch.setattr(recovery_api, "build_outbox_publisher_from_environment", lambda: publisher)
    client = TestClient(app)
    support_reference = _support_reference(client)
    headers = _headers(
        capability="idea.outbox-recovery.redrive",
        idempotency_key="outbox-redrive:api:failure",
    )

    failed = client.post(
        f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive",
        headers=headers,
        json={"reason": "broker_route_corrected", "changeReference": "CHG-2026-0710"},
    )
    conflict = client.post(
        f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive",
        headers=headers,
        json={"reason": "schema_reviewed", "changeReference": "CHG-2026-0710"},
    )

    assert failed.status_code == 200
    assert failed.json()["runStatus"] == "dead_lettered"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    persisted = repository.snapshot().outbox_events[event.event_id]
    assert persisted.status is OutboxEventStatus.DEAD_LETTER
    assert persisted.next_attempt_at_utc is None
    assert len(publisher.events) == 1


def test_dead_letter_redrive_requires_capability_and_idempotency_key() -> None:
    event = _dead_lettered_event()
    reset_idea_repository_for_tests(repository=_repository_with_event(event))
    client = TestClient(app)
    support_reference = _support_reference(client)
    path = f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive"
    body = {"reason": "broker_route_corrected", "changeReference": "CHG-2026-0710"}

    denied = client.post(path, json=body)
    missing_key = client.post(
        path,
        headers=_headers(capability="idea.outbox-recovery.redrive"),
        json=body,
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert missing_key.status_code == 400
    assert missing_key.json()["code"] == "invalid_request"


def test_production_redrive_rejects_untrusted_caller_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    event = _dead_lettered_event()
    repository = _repository_with_event(event)
    reset_idea_repository_for_tests(repository=repository)
    client = TestClient(app)
    support_reference = "outbox-dlq-1234567890abcdef12345678"

    response = client.post(
        f"/api/v1/outbox-delivery/dead-letters/{support_reference}/redrive",
        headers=_headers(
            capability="idea.outbox-recovery.redrive",
            idempotency_key="outbox-redrive:api:untrusted",
        ),
        json={"reason": "broker_route_corrected", "changeReference": "CHG-2026-0710"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert repository.snapshot().outbox_events[event.event_id].status is OutboxEventStatus.DEAD_LETTER


class RecordingPublisher:
    def __init__(self, *, accepted: bool) -> None:
        self.accepted = accepted
        self.events = []
        self.close_count = 0

    def publish(self, event):
        self.events.append(event)
        if self.accepted:
            return OutboxPublishOutcome.accepted_by_publisher()
        return OutboxPublishOutcome.rejected_by_publisher("publisher_rejected_again")

    def close(self) -> None:
        self.close_count += 1


def _support_reference(client: TestClient) -> str:
    response = client.get(
        "/api/v1/outbox-delivery/dead-letters",
        headers=_headers(capability="idea.outbox-recovery.read"),
    )
    assert response.status_code == 200
    return response.json()["items"][0]["supportReference"]


def _headers(*, capability: str, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": capability,
        "X-Correlation-Id": "corr-outbox-recovery-api",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _dead_lettered_event():
    event = build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="candidate-sensitive",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
        idempotency_key="candidate-secret-key",
    )
    return mark_outbox_event_failed(
        event,
        failure_reason="publisher_rejected",
        failed_at_utc=EVENT_TIME + timedelta(minutes=1),
        max_retry_count=1,
        next_attempt_at_utc=None,
    )


def _repository_with_event(event):
    return InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={},
            report_evidence_pack_candidates={},
            ai_explanation_lineage_candidates={},
            outbox_events={event.event_id: event},
            downstream_submission_records={},
        )
    )
