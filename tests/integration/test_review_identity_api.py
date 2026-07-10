from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    feedback_headers,
    feedback_payload,
    persisted_candidate_id,
    review_headers,
    suppress_review_payload,
)


def test_review_action_api_governs_resource_identity_across_transport_keys() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-identity-001")
    resource_id = "review-resource-identity-api-001"
    request = suppress_review_payload(review_id=resource_id)
    route = f"/api/v1/idea-candidates/{candidate_id}/review-actions"

    first = client.post(
        route,
        json=request,
        headers=review_headers("review-resource-identity-api-first"),
    )
    before_retry = get_idea_repository().snapshot()
    replayed = client.post(
        route,
        json=request,
        headers=review_headers("review-resource-identity-api-retry"),
    )
    changed_request = dict(request)
    changed_request["decidedAtUtc"] = "2026-06-21T10:05:01Z"
    conflict = client.post(
        route,
        json=changed_request,
        headers=review_headers("review-resource-identity-api-changed"),
    )
    after_retry = get_idea_repository().snapshot()

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["reviewDecision"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "review_identity_conflict"
    assert after_retry.candidate_records == before_retry.candidate_records
    assert after_retry.outbox_events == before_retry.outbox_events


def test_feedback_api_governs_resource_identity_across_transport_keys() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-identity-001")
    resource_id = "feedback-resource-identity-api-001"
    request = feedback_payload(feedback_id=resource_id)
    route = f"/api/v1/idea-candidates/{candidate_id}/feedback"

    first = client.post(
        route,
        json=request,
        headers=feedback_headers("feedback-resource-identity-api-first"),
    )
    before_retry = get_idea_repository().snapshot()
    replayed = client.post(
        route,
        json=request,
        headers=feedback_headers("feedback-resource-identity-api-retry"),
    )
    conflict = client.post(
        route,
        json=feedback_payload(feedback_id=resource_id, outcome="not_useful"),
        headers=feedback_headers("feedback-resource-identity-api-changed"),
    )
    after_retry = get_idea_repository().snapshot()

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["feedbackEvent"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "review_identity_conflict"
    assert after_retry.candidate_records == before_retry.candidate_records
    assert after_retry.outbox_events == before_retry.outbox_events
