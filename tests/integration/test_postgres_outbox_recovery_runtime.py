from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.domain import (
    OutboxEventStatus,
    OutboxRecoveryDecision,
    outbox_dead_letter_support_reference,
    outbox_recovery_request_payload,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.main import app
from app.runtime.repository_state import (
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
)


def test_postgres_outbox_recovery_resolves_exact_support_reference_after_restart(
    postgres_database_url: str,
) -> None:
    del postgres_database_url
    client = TestClient(app)
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-outbox-recovery-001"),
    )
    assert response.status_code == 200
    repository = get_idea_repository()
    assert isinstance(repository, PostgresIdeaRepository)
    event = next(iter(repository.snapshot().outbox_events.values()))
    claimed_at = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)
    claimed = repository.claim_outbox_events_for_delivery(
        limit=1,
        max_retry_count=1,
        lease_owner="postgres-delivery-proof",
        lease_attempt_id="postgres-delivery-attempt",
        claimed_at_utc=claimed_at,
        lease_expires_at_utc=claimed_at + timedelta(minutes=1),
    )
    assert claimed[0].status is OutboxEventStatus.LEASED
    repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="postgres-delivery-proof",
        lease_attempt_id="postgres-delivery-attempt",
        failure_reason="publisher_rejected",
        failed_at_utc=claimed_at + timedelta(minutes=1),
        max_retry_count=1,
    )
    support_reference = outbox_dead_letter_support_reference(event.event_id)
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason="broker_route_corrected",
        change_reference="CHG-POSTGRES-RECOVERY-001",
        actor_subject="platform-operator",
    )
    claim: dict[str, Any] = {
        "support_reference": support_reference,
        "idempotency_key": "outbox-redrive:postgres-runtime:001",
        "request_payload": request_payload,
        "actor_subject": "platform-operator",
        "reason": "broker_route_corrected",
        "change_reference": "CHG-POSTGRES-RECOVERY-001",
        "requested_at_utc": claimed_at + timedelta(minutes=2),
        "lease_owner": "outbox-recovery",
        "lease_attempt_id": "postgres-recovery-attempt",
        "lease_expires_at_utc": claimed_at + timedelta(minutes=7),
    }

    reset_idea_repository_for_tests(reload_from_environment=True)
    restarted = get_idea_repository()
    assert isinstance(restarted, PostgresIdeaRepository)
    accepted = restarted.claim_dead_letter_for_recovery(**claim)
    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = get_idea_repository().claim_dead_letter_for_recovery(**claim)

    assert accepted.decision is OutboxRecoveryDecision.ACCEPTED
    assert accepted.event is not None
    assert accepted.event.status is OutboxEventStatus.LEASED
    assert accepted.audit_record is not None
    assert accepted.audit_record.support_reference == support_reference
    assert replayed.decision is OutboxRecoveryDecision.REPLAYED
    assert replayed.audit_record == accepted.audit_record
