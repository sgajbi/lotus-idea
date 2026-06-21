from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.repository_state import reset_idea_repository_for_tests
from app.main import app


def source_ref(product_id: str, freshness: str = "current") -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": freshness,
    }


def high_cash_payload(*, cash_weight: str = "0.18") -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": cash_weight,
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "entitlementAllowed": True,
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": idempotency_key,
    }


def review_headers(
    idempotency_key: str, capabilities: str = "idea.review.record"
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-review-api",
        "Idempotency-Key": idempotency_key,
    }


def feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "X-Correlation-Id": "corr-feedback-api",
        "Idempotency-Key": idempotency_key,
    }


def access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }


def authorized_scope(portfolio_id: str = "PB_SG_GLOBAL_BAL_001") -> dict[str, list[str]]:
    return {
        "tenantIds": ["tenant-private-bank-sg"],
        "bookIds": ["book-advisor-001"],
        "portfolioIds": [portfolio_id],
        "clientIds": ["client-001"],
    }


def suppress_review_payload(
    *,
    review_id: str = "review-suppress-001",
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
) -> dict[str, Any]:
    return {
        "reviewId": review_id,
        "action": "suppress",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(portfolio_id),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
        "suppressionReason": "manual_suppression",
    }


def approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "review-approve-001",
        "action": "approve_for_conversion",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def feedback_payload() -> dict[str, Any]:
    return {
        "feedbackId": "feedback-useful-001",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "outcome": "useful",
        "reasonCodes": ["review_required"],
        "recordedAtUtc": "2026-06-21T10:06:00Z",
    }


def persisted_candidate_id(client: TestClient, *, idempotency_key: str) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence"]["decision"] == "accepted"
    return str(payload["persistence"]["candidateId"])


def test_review_action_api_persists_suppression_with_audit_posture() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-action-001")

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=review_headers("review-action-api-suppress-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-review-api"
    payload = response.json()
    assert payload["reviewDecision"]["action"] == "suppress"
    assert payload["reviewDecision"]["grantsDownstreamAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["candidateId"] == candidate_id
    assert payload["persistence"]["reviewPosture"] == "suppressed"
    assert payload["persistence"]["auditEventType"] == "idea.review.decision_recorded"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_review_action_api_replays_same_idempotency_payload() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-replay-001")
    headers = review_headers("review-action-api-replay-001")
    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=headers,
    )

    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=headers,
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["reviewDecision"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert replayed.json()["persistence"]["candidateId"] == candidate_id


def test_review_action_api_returns_conflict_for_changed_idempotency_payload() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-conflict-001")
    headers = review_headers("review-action-api-conflict-001")
    client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(review_id="review-suppress-001"),
        headers=headers,
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(review_id="review-suppress-002"),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_conflict"


def test_review_action_api_returns_state_conflict_for_generated_candidate_approval() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-state-001")

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(),
        headers=review_headers("review-action-api-state-conflict-001"),
    )

    assert response.status_code == 409
    assert response.json() == {
        "type": "about:blank",
        "status": 409,
        "code": "review_action_conflict",
        "title": "Review action conflict",
        "detail": "The review action is not valid for the current idea candidate state.",
    }


def test_feedback_api_persists_source_provenanced_feedback() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-001")

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=feedback_headers("feedback-api-useful-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-feedback-api"
    payload = response.json()
    assert payload["feedbackEvent"]["candidateId"] == candidate_id
    assert payload["feedbackEvent"]["outcome"] == "useful"
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["auditEventType"] == "idea.feedback.recorded"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_review_action_api_returns_not_found_for_missing_candidate() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-candidates/missing-candidate/review-actions",
        json=suppress_review_payload(),
        headers=review_headers("review-action-api-missing-001"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "candidate_not_found"


def test_review_action_api_requires_mutating_capability_and_scope() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-denied-001")

    denied_by_capability = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=review_headers("review-action-api-denied-001", capabilities="idea.signal.evaluate"),
    )
    denied_by_scope = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(portfolio_id="different-portfolio"),
        headers=review_headers("review-action-api-denied-002"),
    )

    assert denied_by_capability.status_code == 403
    assert denied_by_capability.json()["code"] == "permission_denied"
    assert denied_by_scope.status_code == 403
    assert denied_by_scope.json()["code"] == "permission_denied"
    assert "different-portfolio" not in denied_by_scope.text


def test_review_action_api_validation_errors_are_product_safe() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-validation-001")
    payload = suppress_review_payload()
    payload["accessScope"]["tenantId"] = " "

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=payload,
        headers=review_headers("review-action-api-validation-001"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


def test_review_action_api_rejects_invalid_identity_time_idempotency_and_actor_role() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-invalid-001")
    blank_review = suppress_review_payload(review_id=" ")
    naive_time = suppress_review_payload()
    naive_time["decidedAtUtc"] = "2026-06-21T10:05:00"

    blank_review_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=blank_review,
        headers=review_headers("review-action-api-invalid-review-id-001"),
    )
    naive_time_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=naive_time,
        headers=review_headers("review-action-api-invalid-time-001"),
    )
    blank_idempotency_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=review_headers(" "),
    )
    ambiguous_role_headers = review_headers("review-action-api-ambiguous-role-001")
    ambiguous_role_headers["X-Caller-Roles"] = "advisor,compliance"
    ambiguous_role_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=ambiguous_role_headers,
    )

    assert blank_review_response.status_code == 400
    assert naive_time_response.status_code == 400
    assert blank_idempotency_response.status_code == 400
    assert ambiguous_role_response.status_code == 403


def test_review_action_api_rejects_invalid_authorized_scope_sets() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-scope-001")
    empty_scope = suppress_review_payload()
    empty_scope["authorizedScope"]["tenantIds"] = []
    blank_scope = suppress_review_payload()
    blank_scope["authorizedScope"]["portfolioIds"] = [" "]

    empty_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=empty_scope,
        headers=review_headers("review-action-api-empty-scope-001"),
    )
    blank_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=blank_scope,
        headers=review_headers("review-action-api-blank-scope-001"),
    )

    assert empty_response.status_code == 400
    assert blank_response.status_code == 400


def test_feedback_api_returns_not_found_and_permission_denied_safely() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-denied-001")
    denied_by_capability = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=review_headers("feedback-api-denied-001", capabilities="idea.review.record"),
    )
    denied_payload = feedback_payload()
    denied_payload["authorizedScope"]["portfolioIds"] = ["different-portfolio"]
    denied_by_scope = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=denied_payload,
        headers=feedback_headers("feedback-api-denied-002"),
    )
    not_found = client.post(
        "/api/v1/idea-candidates/missing-candidate/feedback",
        json=feedback_payload(),
        headers=feedback_headers("feedback-api-missing-001"),
    )

    assert denied_by_capability.status_code == 403
    assert denied_by_scope.status_code == 403
    assert "different-portfolio" not in denied_by_scope.text
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "candidate_not_found"


def test_feedback_api_rejects_invalid_identity_time_and_idempotency() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-invalid-001")
    blank_feedback = feedback_payload()
    blank_feedback["feedbackId"] = " "
    naive_time = feedback_payload()
    naive_time["recordedAtUtc"] = "2026-06-21T10:06:00"

    blank_feedback_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=blank_feedback,
        headers=feedback_headers("feedback-api-invalid-feedback-id-001"),
    )
    naive_time_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=naive_time,
        headers=feedback_headers("feedback-api-invalid-time-001"),
    )
    blank_idempotency_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=feedback_headers(" "),
    )

    assert blank_feedback_response.status_code == 400
    assert naive_time_response.status_code == 400
    assert blank_idempotency_response.status_code == 400
