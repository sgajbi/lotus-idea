from __future__ import annotations

import pytest
from tests.support.http import managed_test_client

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
    client = managed_test_client(app)
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
    self_asserted_payload["accessScope"] = {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_DIFFERENT_999",
        "clientId": "client-001",
    }

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
    assert self_asserted.status_code == 400
    assert self_asserted.json()["code"] == "invalid_request"
    assert "PB_SG_DIFFERENT_999" not in self_asserted.text


def test_feedback_api_enforces_trusted_caller_entitlement_scope() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
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
    self_asserted_payload["authorizedScope"] = {
        "tenantIds": ["tenant-private-bank-sg"],
        "bookIds": ["book-advisor-001"],
        "portfolioIds": ["PB_SG_DIFFERENT_999"],
        "clientIds": ["client-001"],
    }

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
    assert self_asserted.status_code == 400
    assert self_asserted.json()["code"] == "invalid_request"
    assert "PB_SG_DIFFERENT_999" not in self_asserted.text


@pytest.mark.parametrize("mutation", ("review", "feedback"))
@pytest.mark.parametrize(
    ("header_name", "mismatched_value"),
    (
        ("X-Caller-Tenant-Ids", "tenant-other"),
        ("X-Caller-Book-Ids", "book-other"),
        ("X-Caller-Portfolio-Ids", "portfolio-other"),
        ("X-Caller-Client-Ids", "client-other"),
    ),
)
def test_review_mutations_fail_closed_for_each_entitlement_dimension(
    mutation: str,
    header_name: str,
    mismatched_value: str,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-{mutation}-{header_name.lower()}-mismatch-001",
    )
    path, payload, headers = _mutation_request(mutation, candidate_id)
    headers[header_name] = mismatched_value

    response = client.post(path, json=payload, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert mismatched_value not in response.text


@pytest.mark.parametrize("mutation", ("review", "feedback"))
def test_review_mutations_accept_candidate_scope_within_multi_value_entitlements(
    mutation: str,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-{mutation}-multi-value-scope-001",
    )
    path, payload, headers = _mutation_request(mutation, candidate_id)
    headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-other,tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-other,book-advisor-001",
            "X-Caller-Portfolio-Ids": "portfolio-other,PB_SG_GLOBAL_BAL_001",
            "X-Caller-Client-Ids": "client-other,client-001",
        }
    )

    response = client.post(path, json=payload, headers=headers)

    assert response.status_code == 200


def test_review_mutation_openapi_excludes_self_asserted_scope_fields() -> None:
    schemas = app.openapi()["components"]["schemas"]

    for schema_name in ("ReviewActionRequest", "FeedbackRequest"):
        properties = schemas[schema_name]["properties"]
        assert "accessScope" not in properties
        assert "authorizedScope" not in properties


def _mutation_request(
    mutation: str,
    candidate_id: str,
) -> tuple[str, dict[str, object], dict[str, str]]:
    if mutation == "review":
        return (
            f"/api/v1/idea-candidates/{candidate_id}/review-actions",
            suppress_review_payload(),
            review_headers(f"{mutation}-entitlement-regression-001"),
        )
    return (
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        feedback_payload(),
        feedback_headers(f"{mutation}-entitlement-regression-001"),
    )
