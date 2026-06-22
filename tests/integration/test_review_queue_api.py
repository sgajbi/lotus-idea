from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app


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


def access_scope(*, portfolio_id: str = "PB_SG_GLOBAL_BAL_001") -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": portfolio_id,
        "clientId": "client-001",
    }


def high_cash_payload(
    *,
    cash_weight: str,
    suffix: str = "",
    candidate_scope: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": cash_weight,
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1", suffix),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1", suffix),
            "cashflowProjectionRef": source_ref(
                "lotus-core:PortfolioCashflowProjection:v1", suffix
            ),
        },
        "accessScope": candidate_scope,
        "entitlementAllowed": True,
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": idempotency_key,
    }


def queue_headers(capabilities: str = "idea.review.queue.read") -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-review-queue-api",
    }


def readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.review.queue.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-review-queue-readiness-api",
    }


def persist_candidate(
    client: TestClient,
    *,
    cash_weight: str,
    suffix: str,
    idempotency_key: str,
    candidate_scope: dict[str, str] | None = None,
) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(
            cash_weight=cash_weight,
            suffix=suffix,
            candidate_scope=candidate_scope,
        ),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def test_advisor_review_queue_api_projects_persisted_candidates() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    first = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-first",
        idempotency_key="seed-review-queue-001",
    )
    second = persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-second",
        idempotency_key="seed-review-queue-002",
    )

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=queue_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-review-queue-api"
    payload = response.json()
    assert payload["policyVersion"] == "idea-deterministic-ranking-v1"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert [item["candidate"]["candidateId"] for item in payload["items"]] == sorted(
        [first, second]
    )
    assert [item["rank"] for item in payload["items"]] == [1, 2]
    assert payload["exclusions"] == []


def test_advisor_review_queue_api_filters_candidates_by_access_scope() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    included = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-included",
        idempotency_key="seed-review-queue-scope-001",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
    )
    excluded = persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-excluded",
        idempotency_key="seed-review-queue-scope-002",
        candidate_scope=access_scope(portfolio_id="PB_SG_ALT_BAL_002"),
    )

    response = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            "&tenantId=tenant-private-bank-sg&bookId=book-advisor-001"
            "&portfolioId=PB_SG_GLOBAL_BAL_001&clientId=client-001"
        ),
        headers=queue_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["candidate"]["candidateId"] for item in payload["items"]] == [included]
    assert payload["exclusions"] == [
        {
            "candidateId": excluded,
            "reason": "access_scope_mismatch",
            "detail": "candidate is outside the requested advisor access scope",
        }
    ]


def test_advisor_review_queue_api_returns_empty_queue_without_candidates() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=queue_headers(),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["exclusions"] == []


def test_advisor_review_queue_api_requires_read_permission() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers={
            "X-Caller-Subject": "viewer-001",
            "X-Caller-Roles": "viewer",
            "X-Caller-Capabilities": "idea.signal.evaluate",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to read advisor idea review queues.",
    }


def test_advisor_review_queue_api_rejects_naive_evaluation_time_safely() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00",
        headers=queue_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "evaluatedAtUtc must be timezone-aware.",
    }


def test_advisor_review_queue_api_rejects_blank_scope_filter_safely() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&portfolioId=",
        headers=queue_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Scope query fields cannot be blank.",
    }


def test_advisor_review_queue_readiness_api_returns_source_safe_operator_posture() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    first = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-readiness-first",
        idempotency_key="seed-review-queue-readiness-001",
    )
    second = persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-readiness-second",
        idempotency_key="seed-review-queue-readiness-002",
    )

    response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=readiness_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-review-queue-readiness-api"
    payload = response.json()
    assert payload == {
        "repository": "lotus-idea",
        "policyVersion": "idea-deterministic-ranking-v1",
        "evaluatedAtUtc": "2026-06-21T10:10:00Z",
        "queueProjectionAvailable": True,
        "candidateSnapshotCount": 2,
        "reviewableItemCount": 2,
        "excludedCandidateCount": 0,
        "exclusionCounts": {
            "suppressed": 0,
            "duplicate": 0,
            "expired": 0,
            "closed": 0,
            "rejected": 0,
            "unsupported_evidence": 0,
            "snoozed": 0,
            "unscored": 0,
            "non_reviewable_status": 0,
            "access_scope_mismatch": 0,
        },
        "scoredCandidateCount": 2,
        "unscoredCandidateCount": 0,
        "durableStorageBacked": False,
        "readinessStatus": "blocked",
        "supportabilityStatus": "not_certified",
        "certificationReady": False,
        "certificationBlockers": [
            "durable_repository_not_configured",
            "platform_caller_context_entitlement_proof_missing",
            "workbench_product_proof_missing",
            "data_product_certification_missing",
            "certified_runtime_trust_telemetry_missing",
        ],
        "supportedFeaturePromoted": False,
    }
    assert first not in response.text
    assert second not in response.text
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


def test_advisor_review_queue_readiness_api_requires_operator_permission() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=queue_headers(),
    )
    role_denied = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=readiness_headers(capabilities="idea.review.queue.read"),
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to read idea review queue readiness.",
    }
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_advisor_review_queue_readiness_api_rejects_naive_evaluation_time_safely() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00",
        headers=readiness_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "evaluatedAtUtc must be timezone-aware.",
    }
