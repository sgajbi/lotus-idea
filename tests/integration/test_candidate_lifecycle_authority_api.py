from __future__ import annotations

import pytest
from tests.support.http import managed_test_client

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    approve_review_payload,
    conversion_intent_headers,
    conversion_intent_payload,
    lifecycle_headers,
    lifecycle_payload,
    persisted_candidate_id,
    review_headers,
    transition_candidate_to_review_ready,
)


def test_owned_review_and_conversion_use_acceptance_chronology_and_retain_observed_time() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key="seed-owned-control-chronology-001",
    )
    transition_candidate_to_review_ready(client, candidate_id)

    review_request = approve_review_payload(candidate_id)
    review_request["decidedAtUtc"] = "2026-06-21T09:05:00Z"
    reviewed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=review_request,
        headers=review_headers("owned-control-review-001"),
    )
    conversion_request = conversion_intent_payload(conversion_intent_id="owned-control-intent-001")
    conversion_request["requestedAtUtc"] = "2026-06-21T10:10:00Z"
    converted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_request,
        headers=conversion_intent_headers("owned-control-intent-001"),
    )

    assert reviewed.status_code == 200
    assert converted.status_code == 200
    snapshot = get_idea_repository().snapshot()
    record = snapshot.candidate_records[candidate_id]
    assert record.review_decisions[-1].decided_at_utc.isoformat() == "2026-06-21T09:05:00+00:00"
    assert record.review_decisions[-1].accepted_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert record.conversion_intents[-1].intent.requested_at_utc.isoformat() == (
        "2026-06-21T10:10:00+00:00"
    )
    assert record.conversion_intents[-1].accepted_at_utc.isoformat() == (
        "2026-06-21T10:15:00+00:00"
    )
    assert {entry.changed_at_utc.isoformat() for entry in record.lifecycle_history[-2:]} == {
        "2026-06-21T10:15:00+00:00"
    }
    outbox_by_type = {event.event_type: event for event in snapshot.outbox_events.values()}
    review_event = outbox_by_type["idea.review.decision_recorded.v1"]
    conversion_event = outbox_by_type["idea.conversion.intent_requested.v1"]
    assert review_event.occurred_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert review_event.payload["observed_at_utc"] == "2026-06-21T09:05:00+00:00"
    assert conversion_event.occurred_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert conversion_event.payload["observed_at_utc"] == "2026-06-21T10:10:00+00:00"


def test_lifecycle_transition_api_records_idempotent_transition() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-lifecycle-api-001")
    headers = lifecycle_headers("lifecycle-api-replay-001")
    request = lifecycle_payload()

    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=request,
        headers=headers,
    )
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=request,
        headers=headers,
    )

    assert first.status_code == 200
    assert first.headers["X-Correlation-Id"] == "corr-lifecycle-api"
    payload = first.json()
    assert payload["transition"]["transitionId"] == "lifecycle-enriched-001"
    assert payload["transition"]["changedAtUtc"] == "2026-06-21T10:01:00Z"
    assert payload["transition"]["acceptedAtUtc"] == "2026-06-21T10:15:00Z"
    assert payload["transition"]["grantsDownstreamAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["candidateId"] == candidate_id
    assert payload["persistence"]["lifecycleStatus"] == "enriched"
    assert payload["persistence"]["auditEventType"] == "idea.lifecycle.transitioned"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert replayed.status_code == 200
    assert replayed.json()["transition"] == payload["transition"]
    assert replayed.json()["persistence"]["decision"] == "replayed"

    snapshot = get_idea_repository().snapshot()
    record = snapshot.candidate_records[candidate_id]
    assert record.candidate.updated_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert record.lifecycle_history[-1].changed_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    lifecycle_audit = record.audit_events[-1]
    assert lifecycle_audit.occurred_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert lifecycle_audit.attributes["observed_at_utc"] == "2026-06-21T10:01:00+00:00"
    lifecycle_outbox = next(
        event
        for event in snapshot.outbox_events.values()
        if event.event_type == "idea.lifecycle.transitioned.v1"
    )
    assert lifecycle_outbox.occurred_at_utc.isoformat() == "2026-06-21T10:15:00+00:00"
    assert lifecycle_outbox.payload["observed_at_utc"] == "2026-06-21T10:01:00+00:00"


@pytest.mark.parametrize(
    "changed_at_utc",
    ("2000-01-01T00:00:00Z", "2026-06-21T10:20:01Z"),
)
def test_lifecycle_transition_api_rejects_observed_time_outside_control_window(
    changed_at_utc: str,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key=f"seed-{changed_at_utc}")
    before = get_idea_repository().snapshot()

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(changed_at_utc=changed_at_utc),
        headers=lifecycle_headers(f"lifecycle-{changed_at_utc}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert get_idea_repository().snapshot() == before


@pytest.mark.parametrize(
    "target_status",
    (
        "reviewed_by_advisor",
        "approved",
        "converted_to_proposal",
        "converted_to_manage_review",
        "converted_to_report",
        "rejected",
        "expired",
        "closed",
    ),
)
def test_generic_lifecycle_api_rejects_owned_workflow_statuses_without_evidence(
    target_status: str,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-owned-status-{target_status}",
    )
    before = get_idea_repository().snapshot()

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(
            transition_id=f"owned-status-{target_status}",
            target_status=target_status,
        ),
        headers=lifecycle_headers(f"owned-status-{target_status}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert get_idea_repository().snapshot() == before
