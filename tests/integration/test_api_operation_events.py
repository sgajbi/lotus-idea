from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.ai_governance as ai_governance_api
import app.api.candidate_detail as candidate_detail_api
import app.api.candidate_evidence_replay as candidate_evidence_replay_api
import app.api.candidate_lifecycle as candidate_lifecycle_api
import app.api.conversion_governance as conversion_governance_api
import app.api.idea_signals as idea_signals_api
import app.api.report_evidence as report_evidence_api
import app.api.review_queues as review_queues_api
import app.api.review_workflow as review_workflow_api
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app


OperationEventCall = tuple[str, str, str, bool, str | None]


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


def mandate_restriction_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "restrictionRef": {
            "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "sourceSystem": "lotus-advise",
            "productVersion": "v1",
            "route": "/advisory/policy-evaluations/pev_001/restriction-posture",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:mandate-restriction-review",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "restrictionStatus": "REVIEW_REQUIRED",
        "changedSinceLastReview": True,
        "actionabilityBlocked": True,
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


def queue_readiness_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": "idea.review.queue.readiness.read",
        "X-Correlation-Id": "corr-operation-queue-readiness-api",
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


def conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "X-Correlation-Id": "corr-operation-conversion-intent-api",
        "Idempotency-Key": idempotency_key,
    }


def conversion_outcome_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": "idea.conversion.outcome.record",
        "X-Correlation-Id": "corr-operation-conversion-outcome-api",
        "Idempotency-Key": idempotency_key,
    }


def report_evidence_pack_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
        "X-Correlation-Id": "corr-operation-report-evidence-pack-api",
        "Idempotency-Key": idempotency_key,
    }


def ai_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.ai-explanation.evaluate",
        "X-Correlation-Id": "corr-operation-ai-api",
    }


def ai_readiness_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": "idea.ai-explanation.readiness.read",
        "X-Correlation-Id": "corr-operation-ai-readiness-api",
    }


def detail_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.candidate.detail.read",
        "X-Correlation-Id": "corr-operation-detail-api",
    }


def evidence_replay_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "ops-001",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": "idea.candidate.evidence.replay",
        "X-Correlation-Id": "corr-operation-evidence-replay-api",
    }


def evidence_replay_payload(*, suffix: str) -> dict[str, Any]:
    return {
        "evaluatedAtUtc": "2026-06-21T10:30:00Z",
        "currentSourceRefs": [
            source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix),
            source_ref("lotus-core:HoldingsAsOf:v1", suffix),
            source_ref("lotus-core:PortfolioCashMovementSummary:v1", suffix),
            source_ref("lotus-core:PortfolioCashflowProjection:v1", suffix),
        ],
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


def approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "operation-review-approve-001",
        "action": "approve_for_conversion",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "operation-conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def conversion_outcome_payload() -> dict[str, Any]:
    return {
        "conversionOutcomeId": "operation-conversion-outcome-001",
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "downstreamReference": "operation-report-evidence-pack-001",
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def report_evidence_pack_payload() -> dict[str, Any]:
    return {
        "reportEvidencePackId": "operation-report-evidence-pack-001",
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": False,
    }


def ai_payload() -> dict[str, Any]:
    return {
        "requestId": "operation-ai-explanation-001",
        "workflowPack": {
            "workflowPackId": "lotus-ai:idea-explanation:v1",
            "workflowPackVersion": "v1",
            "purpose": "missing_evidence_check",
            "evaluationRef": "lotus-ai:governed-verifier:v1",
        },
        "approvedMetadata": {"channel": "advisor-workbench"},
        "requestedAtUtc": "2026-06-21T10:12:00Z",
        "fallbackReason": "ai_unavailable",
    }


def capture_operation_events(
    monkeypatch: pytest.MonkeyPatch,
    *modules: Any,
) -> list[OperationEventCall]:
    events: list[OperationEventCall] = []

    def capture_foundation_event(
        operation: Any,
        outcome: Any,
        *,
        source_authority: str = "lotus-idea",
        durable_storage_backed: bool = False,
        error_code: str | None = None,
    ) -> None:
        events.append(
            (operation.value, outcome.value, source_authority, durable_storage_backed, error_code)
        )

    def capture_operation_event(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.source_authority,
                event.durable_storage_backed,
                event.error_code,
            )
        )

    for module in modules:
        if hasattr(module, "emit_foundation_operation_event"):
            monkeypatch.setattr(module, "emit_foundation_operation_event", capture_foundation_event)
        if hasattr(module, "emit_operation_event"):
            monkeypatch.setattr(module, "emit_operation_event", capture_operation_event)
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
        )
        | {"changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z"},
        headers=lifecycle_headers(idempotency_key),
    )
    assert response.status_code == 200
    assert response.json()["persistence"]["decision"] == "accepted"


def approve_candidate_for_conversion(client: TestClient, candidate_id: str) -> None:
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transition_candidate(
            client,
            candidate_id,
            target_status=target_status,
            idempotency_key=f"operation-lifecycle-{target_status}-001",
            transition_id=f"operation-lifecycle-{target_status}-001",
            minute=index,
        )
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(),
        headers=review_headers("operation-review-approved-conversion-001"),
    )
    assert response.status_code == 200
    assert response.json()["persistence"]["reviewPosture"] == "approved_for_conversion"


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
        ("signal_evaluation", "accepted", "lotus-core", False, None),
        ("candidate_persistence", "accepted", "lotus-core", False, None),
    ]


def test_mandate_restriction_signal_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)
    events = capture_operation_events(monkeypatch, idea_signals_api)

    response = client.post(
        "/api/v1/idea-signals/mandate-restriction/evaluate",
        json=mandate_restriction_payload(),
        headers=signal_headers(),
    )

    assert response.status_code == 200
    assert events == [("signal_evaluation", "accepted", "lotus-advise", False, None)]


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
    queue_readiness_response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=queue_readiness_headers(),
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
    assert queue_readiness_response.status_code == 200
    assert review_response.status_code == 200
    assert feedback_response.status_code == 200
    assert lifecycle_events == [("lifecycle_transition", "accepted", "lotus-idea", False, None)]
    assert queue_events == [
        ("review_queue_read", "accepted", "lotus-idea", False, None),
        ("review_queue_readiness_read", "blocked", "lotus-idea", False, None),
    ]
    assert review_events == [
        ("review_action", "accepted", "lotus-idea", False, None),
        ("feedback_record", "accepted", "lotus-idea", False, None),
    ]


def test_ai_explanation_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    events = capture_operation_events(monkeypatch, ai_governance_api)
    candidate_id = persist_candidate(
        client,
        suffix="-ai-explanation",
        idempotency_key="operation-persist-ai-001",
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_payload(),
        headers=ai_headers(),
    )

    assert response.status_code == 200
    assert events == [("ai_explanation", "fallback", "lotus-idea", False, None)]


def test_ai_explanation_readiness_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)
    events: list[tuple[str, str, str, str, bool, str | None]] = []

    def capture_event(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.source_authority,
                event.supportability_status.value,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(ai_governance_api, "emit_operation_event", capture_event)

    response = client.get(
        "/api/v1/ai-explanations/readiness",
        headers=ai_readiness_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "ai_explanation_readiness_read",
            "blocked",
            "lotus-ai",
            "not_certified",
            False,
            None,
        )
    ]


def test_candidate_detail_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    events = capture_operation_events(monkeypatch, candidate_detail_api)
    candidate_id = persist_candidate(
        client,
        suffix="-candidate-detail",
        idempotency_key="operation-persist-detail-001",
    )

    response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=detail_headers(),
    )

    assert response.status_code == 200
    assert events == [("candidate_detail_read", "accepted", "lotus-idea", False, None)]


def test_candidate_evidence_replay_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    events = capture_operation_events(monkeypatch, candidate_evidence_replay_api)
    candidate_id = persist_candidate(
        client,
        suffix="-candidate-evidence-replay",
        idempotency_key="operation-persist-evidence-replay-001",
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=evidence_replay_payload(suffix="-candidate-evidence-replay"),
        headers=evidence_replay_headers(),
    )

    assert response.status_code == 200
    assert events == [("candidate_evidence_replay", "accepted", "lotus-idea", False, None)]


def test_conversion_and_report_workflow_emit_operation_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    conversion_events = capture_operation_events(monkeypatch, conversion_governance_api)
    report_events = capture_operation_events(monkeypatch, report_evidence_api)
    candidate_id = persist_candidate(
        client,
        suffix="-conversion-report-events",
        idempotency_key="operation-persist-conversion-report-001",
    )
    approve_candidate_for_conversion(client, candidate_id)

    intent_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers("operation-conversion-intent-accepted-001"),
    )
    outcome_response = client.post(
        "/api/v1/conversion-intents/operation-conversion-report-001/outcomes",
        json=conversion_outcome_payload(),
        headers=conversion_outcome_headers("operation-conversion-outcome-accepted-001"),
    )
    report_response = client.post(
        "/api/v1/conversion-intents/operation-conversion-report-001/report-evidence-packs",
        json=report_evidence_pack_payload(),
        headers=report_evidence_pack_headers("operation-report-evidence-pack-accepted-001"),
    )

    assert intent_response.status_code == 200
    assert outcome_response.status_code == 200
    assert report_response.status_code == 200
    assert conversion_events == [
        ("conversion_intent", "accepted", "lotus-idea", False, None),
        ("conversion_outcome", "accepted", "lotus-idea", False, None),
    ]
    assert report_events == [("report_evidence_pack", "accepted", "lotus-report", False, None)]
