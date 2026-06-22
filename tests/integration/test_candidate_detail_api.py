from __future__ import annotations

import asyncio
from typing import Any

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.candidate_detail import get_idea_candidate_detail
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.application.candidate_detail import GetCandidateDetailCommand
from app.main import app


def source_ref(product_id: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def high_cash_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
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


def detail_headers(capabilities: str = "idea.candidate.detail.read") -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-candidate-detail-api",
    }


def lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "Idempotency-Key": idempotency_key,
    }


def review_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "Idempotency-Key": idempotency_key,
    }


def feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "Idempotency-Key": idempotency_key,
    }


def conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "Idempotency-Key": idempotency_key,
    }


def conversion_outcome_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": "idea.conversion.outcome.record",
        "Idempotency-Key": idempotency_key,
    }


def report_evidence_pack_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
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


def persisted_candidate_id(client: TestClient, *, idempotency_key: str) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def lifecycle_payload(target_status: str, *, minute: int) -> dict[str, Any]:
    return {
        "transitionId": f"detail-lifecycle-{target_status}",
        "targetLifecycleStatus": target_status,
        "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
        "reasonCodes": ["review_required"],
    }


def transition_candidate_to_review_ready(client: TestClient, candidate_id: str) -> None:
    for minute, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=lifecycle_payload(target_status, minute=minute),
            headers=lifecycle_headers(f"detail-lifecycle-{target_status}-001"),
        )
        assert response.status_code == 200


def approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "detail-review-approve-001",
        "action": "approve_for_conversion",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def feedback_payload() -> dict[str, Any]:
    return {
        "feedbackId": "detail-feedback-useful-001",
        "accessScope": access_scope(),
        "authorizedScope": authorized_scope(),
        "outcome": "useful",
        "reasonCodes": ["review_required"],
        "recordedAtUtc": "2026-06-21T10:06:00Z",
    }


def conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "detail-conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def conversion_outcome_payload() -> dict[str, Any]:
    return {
        "conversionOutcomeId": "detail-conversion-outcome-001",
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "downstreamReference": "detail-report-evidence-pack-001",
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def report_evidence_pack_payload() -> dict[str, Any]:
    return {
        "reportEvidencePackId": "detail-report-evidence-pack-001",
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": False,
    }


def seed_full_candidate_workflow(client: TestClient, candidate_id: str) -> None:
    transition_candidate_to_review_ready(client, candidate_id)
    assert (
        client.post(
            f"/api/v1/idea-candidates/{candidate_id}/review-actions",
            json=approve_review_payload(),
            headers=review_headers("detail-review-approve-001"),
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/idea-candidates/{candidate_id}/feedback",
            json=feedback_payload(),
            headers=feedback_headers("detail-feedback-001"),
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
            json=conversion_intent_payload(),
            headers=conversion_intent_headers("detail-conversion-intent-001"),
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/conversion-intents/detail-conversion-report-001/outcomes",
            json=conversion_outcome_payload(),
            headers=conversion_outcome_headers("detail-conversion-outcome-001"),
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/conversion-intents/detail-conversion-report-001/report-evidence-packs",
            json=report_evidence_pack_payload(),
            headers=report_evidence_pack_headers("detail-report-pack-001"),
        ).status_code
        == 200
    )


def test_candidate_detail_api_returns_source_safe_persisted_candidate_detail() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="detail-seed-basic-001")

    response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=detail_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-candidate-detail-api"
    payload = response.json()
    assert payload["candidate"]["candidateId"] == candidate_id
    assert payload["candidate"]["family"] == "high_cash"
    assert payload["candidate"]["supportability"] == "ready"
    assert payload["evidence"]["evidenceContentHash"].startswith("sha256:")
    assert payload["evidence"]["sourceRefs"]
    assert "route" not in payload["evidence"]["sourceRefs"][0]
    assert "contentHash" not in payload["evidence"]["sourceRefs"][0]
    assert payload["auditSummary"]["eventCount"] == 1
    assert payload["auditSummary"]["latestEventType"] == "idea.candidate.persisted"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_candidate_detail_api_returns_workflow_summaries_without_authority_promotion() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="detail-seed-workflow-001")
    seed_full_candidate_workflow(client, candidate_id)

    response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=detail_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate"]["lifecycleStatus"] == "converted_to_report"
    assert payload["candidate"]["reviewPosture"] == "approved_for_conversion"
    assert [entry["targetStatus"] for entry in payload["lifecycleHistory"]] == [
        "enriched",
        "scored",
        "governance_checked",
        "ready_for_review",
        "approved",
        "converted_to_report",
    ]
    assert payload["reviewDecisions"][0]["grantsDownstreamAuthority"] is False
    assert payload["feedbackEvents"][0]["outcome"] == "useful"
    assert payload["conversionIntents"][0]["targetSourceAuthority"] == "lotus-report"
    assert payload["conversionIntents"][0]["grantsDownstreamAuthority"] is False
    assert payload["conversionOutcomes"][0]["grantsExecutionAuthority"] is False
    assert payload["conversionOutcomes"][0]["grantsClientCommunicationAuthority"] is False
    assert payload["conversionOutcomes"][0]["grantsSuitabilityAuthority"] is False
    assert payload["reportEvidencePacks"][0]["reportSourceAuthority"] == "lotus-report"
    assert payload["reportEvidencePacks"][0]["renderSourceAuthority"] == "lotus-render"
    assert payload["reportEvidencePacks"][0]["archiveSourceAuthority"] == "lotus-archive"
    assert payload["reportEvidencePacks"][0]["createsRenderedOutput"] is False
    assert payload["reportEvidencePacks"][0]["createsArchiveRecord"] is False
    assert payload["reportEvidencePacks"][0]["grantsClientPublicationAuthority"] is False
    assert payload["auditSummary"]["latestEventType"] == "idea.report_evidence_pack.requested"
    assert payload["supportedFeaturePromoted"] is False


def test_candidate_detail_api_requires_permission_and_existing_candidate() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    denied = client.get(
        "/api/v1/idea-candidates/missing-candidate",
        headers={
            "X-Caller-Subject": "viewer-001",
            "X-Caller-Roles": "viewer",
            "X-Caller-Capabilities": "idea.review.queue.read",
        },
    )
    missing = client.get(
        "/api/v1/idea-candidates/missing-candidate",
        headers=detail_headers(),
    )

    assert denied.status_code == 403
    assert denied.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to read idea candidate detail.",
    }
    assert missing.status_code == 404
    assert missing.json() == {
        "type": "about:blank",
        "status": 404,
        "code": "candidate_not_found",
        "title": "Candidate not found",
        "detail": "The idea candidate was not found.",
    }


def test_candidate_detail_api_rejects_blank_candidate_id_safely() -> None:
    reset_idea_repository_for_tests()

    try:
        GetCandidateDetailCommand(candidate_id=" ")
    except ValueError as exc:
        assert str(exc) == "candidate_id is required"
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("blank candidate id should be rejected")

    response = asyncio.run(
        get_idea_candidate_detail(
            candidate_id=" ",
            x_caller_subject="advisor-001",
            x_caller_roles="advisor",
            x_caller_capabilities="idea.candidate.detail.read",
        )
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert response.body
