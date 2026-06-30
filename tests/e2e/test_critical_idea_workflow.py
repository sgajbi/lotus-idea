from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests


PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def _source_ref(product_id: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}:critical-e2e",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def _access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": PORTFOLIO_ID,
        "clientId": "client-001",
    }


def _authorized_scope() -> dict[str, list[str]]:
    return {
        "tenantIds": ["tenant-private-bank-sg"],
        "bookIds": ["book-advisor-001"],
        "portfolioIds": [PORTFOLIO_ID],
        "clientIds": ["client-001"],
    }


def _high_cash_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": _source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": _source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": _source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": _source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "accessScope": _access_scope(),
        "entitlementAllowed": True,
    }


def _headers(
    *,
    subject: str,
    capabilities: str,
    idempotency_key: str | None = None,
    roles: str | None = None,
    correlation_id: str = "corr-critical-idea-workflow-e2e",
) -> dict[str, str]:
    headers = {
        "X-Caller-Subject": subject,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": correlation_id,
    }
    if roles is not None:
        headers["X-Caller-Roles"] = roles
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _queue_headers() -> dict[str, str]:
    headers = _headers(
        subject="advisor-001",
        roles="advisor",
        capabilities="idea.review.queue.read",
    )
    headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-advisor-001",
            "X-Caller-Portfolio-Ids": PORTFOLIO_ID,
            "X-Caller-Client-Ids": "client-001",
        }
    )
    return headers


def _lifecycle_payload(target_status: str, *, minute: int) -> dict[str, Any]:
    return {
        "transitionId": f"critical-e2e-lifecycle-{target_status}",
        "targetLifecycleStatus": target_status,
        "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
        "reasonCodes": ["review_required"],
    }


def _approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "critical-e2e-review-approve-001",
        "action": "approve_for_conversion",
        "accessScope": _access_scope(),
        "authorizedScope": _authorized_scope(),
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def _conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "critical-e2e-conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def _report_evidence_pack_payload(
    *,
    report_evidence_pack_id: str = "critical-e2e-report-evidence-pack-001",
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


def test_critical_idea_workflow_preserves_authority_boundaries() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    candidate_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(),
        headers=_headers(
            subject="signal-ingestion-worker",
            capabilities="idea.candidate.persist",
            idempotency_key="critical-e2e-candidate-001",
        ),
    )

    assert candidate_response.status_code == 200
    candidate_payload = candidate_response.json()
    candidate_id = candidate_payload["persistence"]["candidateId"]
    assert candidate_payload["evaluation"]["outcome"] == "candidate_created"
    assert candidate_payload["evaluation"]["candidate"]["candidateId"] == candidate_id
    assert candidate_payload["evaluation"]["candidate"]["lifecycleStatus"] == "generated"
    assert candidate_payload["persistence"]["decision"] == "accepted"
    assert candidate_payload["supportedFeaturePromoted"] is False

    queue_response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&limit=10",
        headers=_queue_headers(),
    )

    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    assert queue_payload["page"]["returnedItemCount"] == 1
    assert queue_payload["page"]["hasNextPage"] is False
    assert queue_payload["items"][0]["candidate"]["candidateId"] == candidate_id
    assert queue_payload["items"][0]["rank"] == 1
    assert queue_payload["items"][0]["candidate"]["reviewPosture"] == "advisor_review_required"
    assert queue_payload["supportedFeaturePromoted"] is False

    for minute, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        lifecycle_response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=_lifecycle_payload(target_status, minute=minute),
            headers=_headers(
                subject="idea-lifecycle-worker",
                capabilities="idea.candidate.lifecycle.transition",
                idempotency_key=f"critical-e2e-lifecycle-{target_status}-001",
            ),
        )
        assert lifecycle_response.status_code == 200
        assert lifecycle_response.json()["persistence"]["lifecycleStatus"] == target_status

    review_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=_approve_review_payload(),
        headers=_headers(
            subject="advisor-001",
            roles="advisor",
            capabilities="idea.review.record",
            idempotency_key="critical-e2e-review-approve-001",
        ),
    )

    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["reviewDecision"]["action"] == "approve_for_conversion"
    assert review_payload["reviewDecision"]["grantsDownstreamAuthority"] is False
    assert review_payload["persistence"]["reviewPosture"] == "approved_for_conversion"

    conversion_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=_conversion_intent_payload(),
        headers=_headers(
            subject="advisor-001",
            capabilities="idea.conversion.intent.record",
            idempotency_key="critical-e2e-conversion-intent-001",
        ),
    )

    assert conversion_response.status_code == 200
    conversion_payload = conversion_response.json()
    assert conversion_payload["conversionIntent"]["target"] == "report_evidence"
    assert conversion_payload["conversionIntent"]["targetSourceAuthority"] == "lotus-report"
    assert conversion_payload["conversionIntent"]["boundary"] == "intent_only"
    assert conversion_payload["conversionIntent"]["grantsDownstreamAuthority"] is False
    assert conversion_payload["persistence"]["lifecycleStatus"] == "converted_to_report"

    report_pack_response = client.post(
        "/api/v1/conversion-intents/critical-e2e-conversion-report-001/report-evidence-packs",
        json=_report_evidence_pack_payload(),
        headers=_headers(
            subject="advisor-001",
            capabilities="idea.report-evidence-pack.request",
            idempotency_key="critical-e2e-report-pack-001",
        ),
    )

    assert report_pack_response.status_code == 200
    report_pack_payload = report_pack_response.json()
    evidence_pack = report_pack_payload["reportEvidencePack"]
    assert evidence_pack["reportEvidencePackId"] == "critical-e2e-report-evidence-pack-001"
    assert evidence_pack["boundary"] == "request_only"
    assert evidence_pack["reportSourceAuthority"] == "lotus-report"
    assert evidence_pack["renderSourceAuthority"] == "lotus-render"
    assert evidence_pack["archiveSourceAuthority"] == "lotus-archive"
    assert evidence_pack["grantsClientPublicationAuthority"] is False
    assert evidence_pack["createsRenderedOutput"] is False
    assert evidence_pack["createsArchiveRecord"] is False
    assert "route" not in evidence_pack["sourceSummaries"][0]

    client_ready_response = client.post(
        "/api/v1/conversion-intents/critical-e2e-conversion-report-001/report-evidence-packs",
        json=_report_evidence_pack_payload(
            report_evidence_pack_id="critical-e2e-client-ready-pack-001",
            client_ready_publication_requested=True,
        ),
        headers=_headers(
            subject="advisor-001",
            capabilities="idea.report-evidence-pack.request",
            idempotency_key="critical-e2e-client-ready-report-pack-001",
        ),
    )

    assert client_ready_response.status_code == 409
    assert client_ready_response.json()["code"] == "report_evidence_pack_conflict"
    assert PORTFOLIO_ID not in client_ready_response.text

    detail_response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=_headers(
            subject="advisor-001",
            roles="advisor",
            capabilities="idea.candidate.detail.read",
        ),
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["candidate"]["candidateId"] == candidate_id
    assert detail_payload["candidate"]["lifecycleStatus"] == "converted_to_report"
    assert detail_payload["candidate"]["reviewPosture"] == "approved_for_conversion"
    assert [entry["targetStatus"] for entry in detail_payload["lifecycleHistory"]] == [
        "enriched",
        "scored",
        "governance_checked",
        "ready_for_review",
        "approved",
        "converted_to_report",
    ]
    assert detail_payload["conversionIntents"][0]["grantsDownstreamAuthority"] is False
    assert detail_payload["reportEvidencePacks"][0]["grantsClientPublicationAuthority"] is False
    assert detail_payload["reportEvidencePacks"][0]["createsRenderedOutput"] is False
    assert detail_payload["reportEvidencePacks"][0]["createsArchiveRecord"] is False
    assert detail_payload["durableStorageBacked"] is False
    assert detail_payload["supportedFeaturePromoted"] is False
