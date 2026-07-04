from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    feedback_headers,
    feedback_payload,
    persisted_candidate_id,
    review_headers,
    suppress_review_payload,
)


def test_review_action_api_enforces_trusted_caller_entitlement_scope() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-entitlement-001")
    missing_entitlements = review_headers("review-action-api-missing-entitlements-001")
    for header_name in (
        "X-Caller-Tenant-Ids",
        "X-Caller-Book-Ids",
        "X-Caller-Portfolio-Ids",
        "X-Caller-Client-Ids",
    ):
        missing_entitlements.pop(header_name)
    mismatched_entitlements = review_headers("review-action-api-mismatched-entitlements-001")
    mismatched_entitlements["X-Caller-Portfolio-Ids"] = "PB_SG_DIFFERENT_999"
    self_asserted_payload = suppress_review_payload()
    self_asserted_payload["accessScope"]["portfolioId"] = "PB_SG_DIFFERENT_999"
    self_asserted_payload["authorizedScope"]["portfolioIds"] = ["PB_SG_DIFFERENT_999"]

    missing = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=missing_entitlements,
    )
    mismatched = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=mismatched_entitlements,
    )
    self_asserted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=self_asserted_payload,
        headers=mismatched_entitlements,
    )

    assert missing.status_code == 403
    assert missing.json()["code"] == "permission_denied"
    assert mismatched.status_code == 403
    assert mismatched.json()["code"] == "permission_denied"
    assert self_asserted.status_code == 403
    assert self_asserted.json()["code"] == "permission_denied"
    assert "PB_SG_DIFFERENT_999" not in self_asserted.text


def test_feedback_api_enforces_trusted_caller_entitlement_scope() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-entitlement-001")
    missing_entitlements = feedback_headers("feedback-api-missing-entitlements-001")
    for header_name in (
        "X-Caller-Tenant-Ids",
        "X-Caller-Book-Ids",
        "X-Caller-Portfolio-Ids",
        "X-Caller-Client-Ids",
    ):
        missing_entitlements.pop(header_name)
    mismatched_entitlements = feedback_headers("feedback-api-mismatched-entitlements-001")
    mismatched_entitlements["X-Caller-Portfolio-Ids"] = "PB_SG_DIFFERENT_999"
    self_asserted_payload = feedback_payload()
    self_asserted_payload["accessScope"]["portfolioId"] = "PB_SG_DIFFERENT_999"
    self_asserted_payload["authorizedScope"]["portfolioIds"] = ["PB_SG_DIFFERENT_999"]

    missing = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=missing_entitlements,
    )
    mismatched = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=mismatched_entitlements,
    )
    self_asserted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=self_asserted_payload,
        headers=mismatched_entitlements,
    )

    assert missing.status_code == 403
    assert missing.json()["code"] == "permission_denied"
    assert mismatched.status_code == 403
    assert mismatched.json()["code"] == "permission_denied"
    assert self_asserted.status_code == 403
    assert self_asserted.json()["code"] == "permission_denied"
    assert "PB_SG_DIFFERENT_999" not in self_asserted.text
