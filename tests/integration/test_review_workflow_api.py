from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
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
        "accessScope": access_scope(),
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
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-review-api",
        "Idempotency-Key": idempotency_key,
    }


def feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-feedback-api",
        "Idempotency-Key": idempotency_key,
    }


def conversion_intent_headers(
    idempotency_key: str,
    capabilities: str = "idea.conversion.intent.record",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-conversion-intent-api",
        "Idempotency-Key": idempotency_key,
    }


def conversion_outcome_headers(
    idempotency_key: str,
    capabilities: str = "idea.conversion.outcome.record",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-conversion-outcome-api",
        "Idempotency-Key": idempotency_key,
    }


def report_evidence_pack_headers(
    idempotency_key: str,
    capabilities: str = "idea.report-evidence-pack.request",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-report-evidence-pack-api",
        "Idempotency-Key": idempotency_key,
    }


def lifecycle_headers(
    idempotency_key: str,
    capabilities: str = "idea.candidate.lifecycle.transition",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-lifecycle-api",
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


def conversion_intent_payload(
    *,
    conversion_intent_id: str = "conversion-report-001",
    target: str = "report_evidence",
) -> dict[str, Any]:
    return {
        "conversionIntentId": conversion_intent_id,
        "target": target,
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def conversion_outcome_payload(
    *,
    conversion_outcome_id: str = "conversion-report-outcome-001",
    source_system: str = "lotus-report",
    downstream_reference: str = "report-evidence-pack-001",
) -> dict[str, Any]:
    return {
        "conversionOutcomeId": conversion_outcome_id,
        "status": "accepted",
        "sourceSystem": source_system,
        "downstreamReference": downstream_reference,
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def report_evidence_pack_payload(
    *,
    report_evidence_pack_id: str = "report-evidence-pack-001",
    client_ready_publication_requested: bool = False,
) -> dict[str, Any]:
    return {
        "reportEvidencePackId": report_evidence_pack_id,
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": client_ready_publication_requested,
    }


def lifecycle_payload(
    *,
    transition_id: str = "lifecycle-enriched-001",
    target_status: str = "enriched",
    changed_at_utc: str = "2026-06-21T10:01:00Z",
) -> dict[str, Any]:
    return {
        "transitionId": transition_id,
        "targetLifecycleStatus": target_status,
        "changedAtUtc": changed_at_utc,
        "reasonCodes": ["review_required"],
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


def transition_candidate(
    client: TestClient,
    candidate_id: str,
    *,
    target_status: str,
    idempotency_key: str,
    transition_id: str,
    minute: int,
) -> None:
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(
            transition_id=transition_id,
            target_status=target_status,
            changed_at_utc=f"2026-06-21T10:{minute:02d}:00Z",
        ),
        headers=lifecycle_headers(idempotency_key),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["lifecycleStatus"] == target_status


def transition_candidate_to_review_ready(client: TestClient, candidate_id: str) -> None:
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transition_candidate(
            client,
            candidate_id,
            target_status=target_status,
            idempotency_key=f"lifecycle-api-{target_status}-001",
            transition_id=f"lifecycle-{target_status}-001",
            minute=index,
        )


def approve_candidate_for_conversion(client: TestClient, candidate_id: str) -> None:
    transition_candidate_to_review_ready(client, candidate_id)
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(),
        headers=review_headers(f"review-approve-for-conversion-{candidate_id}"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence"]["lifecycleStatus"] == "approved"
    assert payload["persistence"]["reviewPosture"] == "approved_for_conversion"


def test_lifecycle_transition_api_records_idempotent_transition() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
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
    assert payload["transition"]["grantsDownstreamAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["candidateId"] == candidate_id
    assert payload["persistence"]["lifecycleStatus"] == "enriched"
    assert payload["persistence"]["auditEventType"] == "idea.lifecycle.transitioned"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert replayed.status_code == 200
    assert replayed.json()["transition"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"


def test_lifecycle_transition_api_returns_safe_conflicts_and_not_found() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-lifecycle-conflict-001")
    headers = lifecycle_headers("lifecycle-api-conflict-001")
    client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(transition_id="lifecycle-enriched-001", target_status="enriched"),
        headers=headers,
    )

    idempotency_conflict = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(transition_id="lifecycle-scored-001", target_status="scored"),
        headers=headers,
    )
    invalid_transition = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(
            transition_id="lifecycle-ready-invalid-001",
            target_status="ready_for_review",
        ),
        headers=lifecycle_headers("lifecycle-api-invalid-transition-001"),
    )
    not_found = client.post(
        "/api/v1/idea-candidates/missing-candidate/lifecycle-transitions",
        json=lifecycle_payload(transition_id="lifecycle-missing-001"),
        headers=lifecycle_headers("lifecycle-api-missing-001"),
    )

    assert idempotency_conflict.status_code == 409
    assert idempotency_conflict.json()["code"] == "idempotency_conflict"
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["code"] == "lifecycle_transition_conflict"
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "candidate_not_found"


def test_lifecycle_transition_api_requires_permission_and_valid_request() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-lifecycle-invalid-001")
    blank_transition = lifecycle_payload(transition_id=" ")
    naive_time = lifecycle_payload(changed_at_utc="2026-06-21T10:01:00")
    no_reasons = lifecycle_payload()
    no_reasons["reasonCodes"] = []

    denied_by_capability = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(),
        headers=lifecycle_headers("lifecycle-api-denied-001", capabilities="idea.signal.evaluate"),
    )
    blank_transition_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=blank_transition,
        headers=lifecycle_headers("lifecycle-api-blank-transition-001"),
    )
    naive_time_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=naive_time,
        headers=lifecycle_headers("lifecycle-api-naive-time-001"),
    )
    no_reasons_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=no_reasons,
        headers=lifecycle_headers("lifecycle-api-no-reasons-001"),
    )
    blank_idempotency_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(),
        headers=lifecycle_headers(" "),
    )

    assert denied_by_capability.status_code == 403
    assert blank_transition_response.status_code == 400
    assert naive_time_response.status_code == 400
    assert no_reasons_response.status_code == 400
    assert blank_idempotency_response.status_code == 400


def test_lifecycle_transition_api_rejects_downstream_authority_statuses_without_outbox() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key="seed-lifecycle-downstream-authority-001",
    )
    approve_candidate_for_conversion(client, candidate_id)

    accepted_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(
            transition_id="lifecycle-accepted-forbidden-001",
            target_status="accepted",
            changed_at_utc="2026-06-21T10:20:00Z",
        ),
        headers=lifecycle_headers("lifecycle-api-accepted-forbidden-001"),
    )
    executed_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(
            transition_id="lifecycle-executed-forbidden-001",
            target_status="executed",
            changed_at_utc="2026-06-21T10:21:00Z",
        ),
        headers=lifecycle_headers("lifecycle-api-executed-forbidden-001"),
    )
    snapshot = get_idea_repository().snapshot()
    record = snapshot.candidate_records[candidate_id]

    assert accepted_response.status_code == 400
    assert accepted_response.json()["code"] == "invalid_request"
    assert executed_response.status_code == 400
    assert executed_response.json()["code"] == "invalid_request"
    assert record.candidate.lifecycle_status.value == "approved"
    assert {entry.target_status.value for entry in record.lifecycle_history}.isdisjoint(
        {"accepted", "executed"}
    )
    lifecycle_outbox_targets = {
        event.payload.get("target_status")
        for event in snapshot.outbox_events.values()
        if event.event_type == "idea.lifecycle.transitioned.v1"
    }
    assert lifecycle_outbox_targets.isdisjoint({"accepted", "executed"})


def test_lifecycle_transition_api_enables_review_approval_without_bypassing_state() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-lifecycle-approval-001")
    transition_candidate_to_review_ready(client, candidate_id)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(),
        headers=review_headers("review-action-api-approved-001"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewDecision"]["action"] == "approve_for_conversion"
    assert payload["reviewDecision"]["grantsDownstreamAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["lifecycleStatus"] == "approved"
    assert payload["persistence"]["reviewPosture"] == "approved_for_conversion"


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


def test_review_action_api_returns_state_conflict_for_generated_candidate_approval(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-state-001")

    with caplog.at_level(logging.INFO, logger="lotus-idea"):
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
    event = next(
        json.loads(record.message)
        for record in caplog.records
        if '"event": "idea.operation.review_action"' in record.message
        and '"error_code": "review_action_conflict"' in record.message
    )
    assert event["candidate_id"] == candidate_id
    assert event["lifecycle_status"] == "generated"
    assert event["review_posture"] == "advisor_review_required"
    assert event["requested_action"] == "approve_for_conversion"
    assert event["policy_version"] == "idea-candidate-state-v1"


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


def test_conversion_intent_api_records_review_approved_candidate_without_downstream_authority() -> (
    None
):
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-conversion-intent-001")
    approve_candidate_for_conversion(client, candidate_id)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers("conversion-intent-api-report-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-conversion-intent-api"
    payload = response.json()
    assert payload["conversionIntent"]["conversionIntentId"] == "conversion-report-001"
    assert payload["conversionIntent"]["target"] == "report_evidence"
    assert payload["conversionIntent"]["targetSourceAuthority"] == "lotus-report"
    assert payload["conversionIntent"]["boundary"] == "intent_only"
    assert payload["conversionIntent"]["grantsDownstreamAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["candidateId"] == candidate_id
    assert payload["persistence"]["lifecycleStatus"] == "converted_to_report"
    assert payload["persistence"]["reviewPosture"] == "approved_for_conversion"
    assert payload["persistence"]["auditEventType"] == "idea.conversion.intent_requested"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_conversion_intent_api_replays_and_conflicts_idempotently() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-conversion-replay-001")
    approve_candidate_for_conversion(client, candidate_id)
    headers = conversion_intent_headers("conversion-intent-api-replay-001")

    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-replay-001"),
        headers=headers,
    )
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-replay-001"),
        headers=headers,
    )
    conflict = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-replay-002"),
        headers=headers,
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["conversionIntent"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_conversion_intent_api_requires_approved_state_permission_and_valid_request() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-conversion-invalid-001")

    invalid_state = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers("conversion-intent-api-state-001"),
    )
    denied = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers(
            "conversion-intent-api-denied-001",
            capabilities="idea.review.record",
        ),
    )
    blank_id = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=" "),
        headers=conversion_intent_headers("conversion-intent-api-blank-001"),
    )
    no_reasons_payload = conversion_intent_payload()
    no_reasons_payload["reasonCodes"] = []
    no_reasons = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=no_reasons_payload,
        headers=conversion_intent_headers("conversion-intent-api-no-reasons-001"),
    )
    naive_time_payload = conversion_intent_payload()
    naive_time_payload["requestedAtUtc"] = "2026-06-21T10:15:00"
    naive_time = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=naive_time_payload,
        headers=conversion_intent_headers("conversion-intent-api-naive-time-001"),
    )
    blank_idempotency = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers(" "),
    )
    missing = client.post(
        "/api/v1/idea-candidates/missing-candidate/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers("conversion-intent-api-missing-001"),
    )

    assert invalid_state.status_code == 409
    assert invalid_state.json()["code"] == "conversion_intent_conflict"
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert blank_id.status_code == 400
    assert no_reasons.status_code == 400
    assert naive_time.status_code == 400
    assert blank_idempotency.status_code == 400
    assert missing.status_code == 404
    assert missing.json()["code"] == "conversion_resource_not_found"


def test_conversion_outcome_api_records_source_authorized_result() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-conversion-outcome-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-outcome-001"),
        headers=conversion_intent_headers("conversion-intent-api-outcome-001"),
    )
    assert intent.status_code == 200

    response = client.post(
        "/api/v1/conversion-intents/conversion-outcome-001/outcomes",
        json=conversion_outcome_payload(),
        headers=conversion_outcome_headers("conversion-outcome-api-report-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-conversion-outcome-api"
    payload = response.json()
    assert payload["conversionOutcome"]["conversionOutcomeId"] == "conversion-report-outcome-001"
    assert payload["conversionOutcome"]["sourceSystem"] == "lotus-report"
    assert payload["conversionOutcome"]["downstreamReference"] == "report-evidence-pack-001"
    assert payload["conversionOutcome"]["boundary"] == "downstream_realization_required"
    assert payload["conversionOutcome"]["grantsExecutionAuthority"] is False
    assert payload["conversionOutcome"]["grantsClientCommunicationAuthority"] is False
    assert payload["conversionOutcome"]["grantsSuitabilityAuthority"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["auditEventType"] == "idea.conversion.outcome_recorded"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_conversion_outcome_api_rejects_wrong_source_not_found_permission_and_replays() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client, idempotency_key="seed-conversion-outcome-invalid-001"
    )
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-outcome-invalid-001"),
        headers=conversion_intent_headers("conversion-intent-api-outcome-invalid-001"),
    )
    assert intent.status_code == 200
    headers = conversion_outcome_headers("conversion-outcome-api-replay-001")

    first = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id="conversion-outcome-replay-001"),
        headers=headers,
    )
    replayed = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id="conversion-outcome-replay-001"),
        headers=headers,
    )
    wrong_source = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(
            conversion_outcome_id="conversion-outcome-wrong-source-001",
            source_system="lotus-manage",
        ),
        headers=conversion_outcome_headers("conversion-outcome-api-wrong-source-001"),
    )
    denied = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id="conversion-outcome-denied-001"),
        headers=conversion_outcome_headers(
            "conversion-outcome-api-denied-001",
            capabilities="idea.review.record",
        ),
    )
    missing = client.post(
        "/api/v1/conversion-intents/missing-intent/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id="conversion-outcome-missing-001"),
        headers=conversion_outcome_headers("conversion-outcome-api-missing-001"),
    )
    blank_outcome = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id=" "),
        headers=conversion_outcome_headers("conversion-outcome-api-blank-id-001"),
    )
    blank_reference_payload = conversion_outcome_payload(
        conversion_outcome_id="conversion-outcome-blank-reference-001"
    )
    blank_reference_payload["downstreamReference"] = " "
    blank_reference = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=blank_reference_payload,
        headers=conversion_outcome_headers("conversion-outcome-api-blank-reference-001"),
    )
    naive_time_payload = conversion_outcome_payload(
        conversion_outcome_id="conversion-outcome-naive-time-001"
    )
    naive_time_payload["recordedAtUtc"] = "2026-06-21T10:20:00"
    naive_time = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=naive_time_payload,
        headers=conversion_outcome_headers("conversion-outcome-api-naive-time-001"),
    )
    blank_idempotency = client.post(
        "/api/v1/conversion-intents/conversion-outcome-invalid-001/outcomes",
        json=conversion_outcome_payload(conversion_outcome_id="conversion-outcome-blank-key-001"),
        headers=conversion_outcome_headers(" "),
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["conversionOutcome"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert wrong_source.status_code == 409
    assert wrong_source.json()["code"] == "conversion_outcome_conflict"
    assert denied.status_code == 403
    assert missing.status_code == 404
    assert blank_outcome.status_code == 400
    assert blank_reference.status_code == 400
    assert naive_time.status_code == 400
    assert blank_idempotency.status_code == 400


def test_report_evidence_pack_api_records_request_without_render_or_archive_authority() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-report-pack-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-report-pack-001"),
        headers=conversion_intent_headers("conversion-intent-api-report-pack-001"),
    )
    assert intent.status_code == 200

    response = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-001/report-evidence-packs",
        json=report_evidence_pack_payload(),
        headers=report_evidence_pack_headers("report-evidence-pack-api-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-report-evidence-pack-api"
    payload = response.json()
    evidence_pack = payload["reportEvidencePack"]
    assert evidence_pack["reportEvidencePackId"] == "report-evidence-pack-001"
    assert evidence_pack["conversionIntentId"] == "conversion-report-pack-001"
    assert evidence_pack["candidateId"] == candidate_id
    assert evidence_pack["reportSourceAuthority"] == "lotus-report"
    assert evidence_pack["renderSourceAuthority"] == "lotus-render"
    assert evidence_pack["archiveSourceAuthority"] == "lotus-archive"
    assert evidence_pack["boundary"] == "request_only"
    assert evidence_pack["grantsClientPublicationAuthority"] is False
    assert evidence_pack["createsRenderedOutput"] is False
    assert evidence_pack["createsArchiveRecord"] is False
    assert evidence_pack["sourceSummaries"]
    assert "route" not in evidence_pack["sourceSummaries"][0]
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["lifecycleStatus"] == "converted_to_report"
    assert payload["persistence"]["auditEventType"] == "idea.report_evidence_pack.requested"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_report_evidence_pack_api_replays_conflicts_and_blocks_client_ready_publication() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-report-pack-invalid-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-report-pack-invalid-001"),
        headers=conversion_intent_headers("conversion-intent-api-report-pack-invalid-001"),
    )
    assert intent.status_code == 200
    headers = report_evidence_pack_headers("report-evidence-pack-api-replay-001")

    first = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-001"),
        headers=headers,
    )
    replayed = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-001"),
        headers=headers,
    )
    conflict = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-002"),
        headers=headers,
    )
    client_ready = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(
            report_evidence_pack_id="report-pack-client-ready-001",
            client_ready_publication_requested=True,
        ),
        headers=report_evidence_pack_headers("report-evidence-pack-api-client-ready-001"),
    )
    denied = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-denied-001"),
        headers=report_evidence_pack_headers(
            "report-evidence-pack-api-denied-001",
            capabilities="idea.review.record",
        ),
    )
    missing = client.post(
        "/api/v1/conversion-intents/missing-intent/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-missing-001"),
        headers=report_evidence_pack_headers("report-evidence-pack-api-missing-001"),
    )
    blank_pack_id = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id=" "),
        headers=report_evidence_pack_headers("report-evidence-pack-api-blank-001"),
    )
    no_reasons_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-no-reasons-001"
    )
    no_reasons_payload["reasonCodes"] = []
    no_reasons = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=no_reasons_payload,
        headers=report_evidence_pack_headers("report-evidence-pack-api-no-reasons-001"),
    )
    blank_retention_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-blank-retention-001"
    )
    blank_retention_payload["retentionPolicyRef"] = " "
    blank_retention = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=blank_retention_payload,
        headers=report_evidence_pack_headers("report-evidence-pack-api-blank-retention-001"),
    )
    naive_time_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-naive-time-001"
    )
    naive_time_payload["requestedAtUtc"] = "2026-06-21T10:25:00"
    naive_time = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=naive_time_payload,
        headers=report_evidence_pack_headers("report-evidence-pack-api-naive-time-001"),
    )
    blank_idempotency = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-invalid-001/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-blank-key-001"),
        headers=report_evidence_pack_headers(" "),
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["reportEvidencePack"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert client_ready.status_code == 409
    assert client_ready.json()["code"] == "report_evidence_pack_conflict"
    assert denied.status_code == 403
    assert missing.status_code == 404
    assert blank_pack_id.status_code == 400
    assert no_reasons.status_code == 400
    assert blank_retention.status_code == 400
    assert naive_time.status_code == 400
    assert blank_idempotency.status_code == 400
