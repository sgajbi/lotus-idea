from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.candidate_lifecycle as candidate_lifecycle_api
import app.api.idea_signals as idea_signals_api
import app.api.review_queues as review_queues_api
import app.api.review_workflow as review_workflow_api
from app.api.repository_state import reset_idea_repository_for_tests
from app.main import app


OperationEventCall = tuple[str, str, str, str | None]


def source_ref(product_id: str, suffix: str = "") -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}{suffix}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def high_cash_payload(*, suffix: str = "") -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1", suffix),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1", suffix),
            "cashflowProjectionRef": source_ref(
                "lotus-core:PortfolioCashflowProjection:v1",
                suffix,
            ),
        },
        "entitlementAllowed": True,
    }


def signal_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-operation-signal-api",
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-operation-persist-api",
        "Idempotency-Key": idempotency_key,
    }


def queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-operation-queue-api",
    }


def lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "X-Correlation-Id": "corr-operation-lifecycle-api",
        "Idempotency-Key": idempotency_key,
    }


def review_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "X-Correlation-Id": "corr-operation-review-api",
        "Idempotency-Key": idempotency_key,
    }


def feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "X-Correlation-Id": "corr-operation-feedback-api",
        "Idempotency-Key": idempotency_key,
    }


def access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }


def authorized_scope() -> dict[str, list[str]]:
    return {
        "tenantIds": ["tenant-private-bank-sg"],
        "bookIds": ["book-advisor-001"],
        "portfolioIds": ["PB_SG_GLOBAL_BAL_001"],
        "clientIds": ["client-001"],
    }


def lifecycle_payload(
    *,
    transition_id: str = "operation-lifecycle-enriched-001",
    target_status: str = "enriched",
) -> dict[str, Any]:
    return {
        "transitionId": transition_id,
        "targetLifecycleStatus": target_status,
        "changedAtUtc": "2026-06-21T10:01:00Z",
        "reasonCodes": ["review_required"],
    }


def review_payload() -> dict[str, Any]:
    return {
        "reviewId": "operation-review-suppress-001",
        "action": "suppress",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
        "suppressionReason": "manual_suppression",
    }


def feedback_payload() -> dict[str, Any]:
    return {
        "feedbackId": "operation-feedback-useful-001",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "outcome": "useful",
        "reasonCodes": ["review_required"],
        "recordedAtUtc": "2026-06-21T10:06:00Z",
    }


def capture_operation_events(
    monkeypatch: pytest.MonkeyPatch,
    *modules: Any,
) -> list[OperationEventCall]:
    events: list[OperationEventCall] = []

    def capture(
        operation: Any,
        outcome: Any,
        *,
        source_authority: str = "lotus-idea",
        error_code: str | None = None,
    ) -> None:
        events.append((operation.value, outcome.value, source_authority, error_code))

    for module in modules:
        monkeypatch.setattr(module, "emit_foundation_operation_event", capture)
    return events


def persist_candidate(client: TestClient, *, suffix: str, idempotency_key: str) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(suffix=suffix),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence"]["decision"] == "accepted"
    return str(payload["persistence"]["candidateId"])


def test_signal_and_candidate_persistence_emit_bounded_operation_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    events = capture_operation_events(monkeypatch, idea_signals_api)

    signal_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(suffix="-signal"),
        headers=signal_headers(),
    )
    persist_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(suffix="-persist"),
        headers=persist_headers("operation-persist-accepted-001"),
    )

    assert signal_response.status_code == 200
    assert persist_response.status_code == 200
    assert events == [
        ("signal_evaluation", "accepted", "lotus-core", None),
        ("candidate_persistence", "accepted", "lotus-core", None),
    ]


def test_lifecycle_queue_review_and_feedback_emit_operation_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    lifecycle_events = capture_operation_events(monkeypatch, candidate_lifecycle_api)
    queue_events = capture_operation_events(monkeypatch, review_queues_api)
    review_events = capture_operation_events(monkeypatch, review_workflow_api)
    lifecycle_candidate_id = persist_candidate(
        client,
        suffix="-lifecycle",
        idempotency_key="operation-persist-lifecycle-001",
    )
    feedback_candidate_id = persist_candidate(
        client,
        suffix="-feedback",
        idempotency_key="operation-persist-feedback-001",
    )

    lifecycle_response = client.post(
        f"/api/v1/idea-candidates/{lifecycle_candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(),
        headers=lifecycle_headers("operation-lifecycle-accepted-001"),
    )
    queue_response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=queue_headers(),
    )
    review_response = client.post(
        f"/api/v1/idea-candidates/{lifecycle_candidate_id}/review-actions",
        json=review_payload(),
        headers=review_headers("operation-review-accepted-001"),
    )
    feedback_response = client.post(
        f"/api/v1/idea-candidates/{feedback_candidate_id}/feedback",
        json=feedback_payload(),
        headers=feedback_headers("operation-feedback-accepted-001"),
    )

    assert lifecycle_response.status_code == 200
    assert queue_response.status_code == 200
    assert review_response.status_code == 200
    assert feedback_response.status_code == 200
    assert lifecycle_events == [("lifecycle_transition", "accepted", "lotus-idea", None)]
    assert queue_events == [("review_queue_read", "accepted", "lotus-idea", None)]
    assert review_events == [
        ("review_action", "accepted", "lotus-idea", None),
        ("feedback_record", "accepted", "lotus-idea", None),
    ]
