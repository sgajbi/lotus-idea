from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, TRUSTED_CALLER_CONTEXT_TOKEN_ENV
from app.domain import InMemoryIdeaRepository, ReviewPosture
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
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
    evaluated_at_utc: str = "2026-06-21T10:00:00Z",
) -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": evaluated_at_utc,
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


def scoped_queue_headers(
    *,
    portfolio_ids: str = "PB_SG_GLOBAL_BAL_001",
    capabilities: str = "idea.review.queue.read",
) -> dict[str, str]:
    headers = queue_headers(capabilities=capabilities)
    headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-advisor-001",
            "X-Caller-Portfolio-Ids": portfolio_ids,
            "X-Caller-Client-Ids": "client-001",
        }
    )
    return headers


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


def operator_exception_headers(
    *,
    role: str = "operator",
    capability: str = "idea.review.queue.exceptions.read",
) -> dict[str, str]:
    headers = role_queue_headers(role=role, capability=capability)
    headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-advisor-001",
            "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
            "X-Caller-Client-Ids": "client-001",
        }
    )
    return headers


def role_queue_headers(*, role: str, capability: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": f"{role}-001",
        "X-Caller-Roles": role,
        "X-Caller-Capabilities": capability,
        "X-Correlation-Id": f"corr-{role}-review-queue",
    }


def persist_candidate(
    client: TestClient,
    *,
    cash_weight: str,
    suffix: str,
    idempotency_key: str,
    candidate_scope: dict[str, str] | None = None,
    evaluated_at_utc: str = "2026-06-21T10:00:00Z",
) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(
            cash_weight=cash_weight,
            suffix=suffix,
            candidate_scope=candidate_scope,
            evaluated_at_utc=evaluated_at_utc,
        ),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def route_persisted_candidates_by_posture(
    postures_by_candidate_id: dict[str, ReviewPosture],
) -> None:
    snapshot = get_idea_repository().snapshot()
    routed_records = dict(snapshot.candidate_records)
    for candidate_id, posture in postures_by_candidate_id.items():
        record = routed_records[candidate_id]
        routed_records[candidate_id] = replace(
            record,
            candidate=replace(record.candidate, review_posture=posture),
        )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(replace(snapshot, candidate_records=routed_records))
    )


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
    assert {item["policyVersion"] for item in payload["items"]} == {"idea-deterministic-ranking-v1"}
    assert {item["candidate"]["scorePolicyVersion"] for item in payload["items"]} == {
        "idle-liquidity-v1"
    }
    assert payload["exclusions"] == []
    assert payload["page"] | {"snapshotToken": None} == {
        "limit": 25,
        "offset": 0,
        "returnedItemCount": 2,
        "totalReviewableItemCount": 2,
        "returnedExclusionCount": 0,
        "totalExcludedCandidateCount": 0,
        "nextOffset": None,
        "hasNextPage": False,
        "snapshotToken": None,
    }
    assert payload["page"]["snapshotToken"].startswith("rqs1_")


def test_business_review_queue_apis_route_only_the_responsible_audience() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    advisor_candidate = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-advisor-audience",
        idempotency_key="seed-review-queue-advisor-audience-001",
    )
    pm_candidate = persist_candidate(
        client,
        cash_weight="0.19",
        suffix="-pm-audience",
        idempotency_key="seed-review-queue-pm-audience-001",
    )
    compliance_candidate = persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-compliance-audience",
        idempotency_key="seed-review-queue-compliance-audience-001",
    )
    route_persisted_candidates_by_posture(
        {
            pm_candidate: ReviewPosture.PM_REVIEW_REQUIRED,
            compliance_candidate: ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        }
    )

    cases = (
        (
            "/api/v1/review-queues/advisor",
            queue_headers(),
            "advisor",
            advisor_candidate,
            "advisor_review_required",
        ),
        (
            "/api/v1/review-queues/portfolio-manager",
            role_queue_headers(
                role="portfolio_manager",
                capability="idea.review.queue.portfolio-manager.read",
            ),
            "portfolio_manager",
            pm_candidate,
            "pm_review_required",
        ),
        (
            "/api/v1/review-queues/compliance",
            role_queue_headers(
                role="compliance",
                capability="idea.review.queue.compliance.read",
            ),
            "compliance",
            compliance_candidate,
            "compliance_review_required",
        ),
    )

    for path, headers, audience, candidate_id, posture in cases:
        response = client.get(f"{path}?evaluatedAtUtc=2026-06-21T10:10:00Z", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["audience"] == audience
        assert [item["candidate"]["candidateId"] for item in payload["items"]] == [candidate_id]
        assert {item["candidate"]["reviewPosture"] for item in payload["items"]} == {posture}
        assert payload["exclusions"] == []


@pytest.mark.parametrize(
    ("path", "headers"),
    (
        (
            "/api/v1/review-queues/portfolio-manager",
            role_queue_headers(role="advisor", capability="idea.review.queue.portfolio-manager.read"),
        ),
        (
            "/api/v1/review-queues/compliance",
            role_queue_headers(role="portfolio_manager", capability="idea.review.queue.compliance.read"),
        ),
    ),
)
def test_role_specific_review_queues_reject_cross_role_callers(
    path: str,
    headers: dict[str, str],
) -> None:
    reset_idea_repository_for_tests()
    response = TestClient(app).get(path, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_operator_exception_queue_reports_support_posture_by_audience() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_ids = tuple(
        persist_candidate(
            client,
            cash_weight=f"0.{18 + index}",
            suffix=f"-operator-exception-{index}",
            idempotency_key=f"seed-review-queue-operator-exception-{index}",
            candidate_scope=access_scope(),
        )
        for index in range(3)
    )
    snapshot = get_idea_repository().snapshot()
    routed_records = dict(snapshot.candidate_records)
    for candidate_id, posture in zip(
        candidate_ids,
        (
            ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            ReviewPosture.PM_REVIEW_REQUIRED,
            ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ),
        strict=True,
    ):
        record = routed_records[candidate_id]
        routed_records[candidate_id] = replace(
            record,
            candidate=replace(record.candidate, review_posture=posture, score=None),
        )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(replace(snapshot, candidate_records=routed_records))
    )

    response = client.get(
        "/api/v1/review-queues/operator/exceptions?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=operator_exception_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [audience["audience"] for audience in payload["audiences"]] == [
        "advisor",
        "portfolio_manager",
        "compliance",
    ]
    assert [audience["candidateSnapshotCount"] for audience in payload["audiences"]] == [1, 1, 1]
    assert [audience["exceptionCounts"]["unscored"] for audience in payload["audiences"]] == [
        1,
        1,
        1,
    ]
    assert payload["totalExceptionCount"] == 3
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert all(candidate_id not in response.text for candidate_id in candidate_ids)


def test_operator_exception_queue_enforces_role_and_entitled_scope() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    wrong_role = client.get(
        "/api/v1/review-queues/operator/exceptions",
        headers=operator_exception_headers(role="advisor"),
    )
    broader_query = client.get(
        "/api/v1/review-queues/operator/exceptions?portfolioId=PB_SG_OTHER_002",
        headers=operator_exception_headers(),
    )

    assert wrong_role.status_code == 403
    assert wrong_role.json()["code"] == "permission_denied"
    assert broader_query.status_code == 403
    assert broader_query.json()["code"] == "permission_denied"


def test_advisor_review_queue_api_defaults_to_active_queue_snapshot() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-active-default",
        idempotency_key="seed-review-queue-active-default-001",
    )

    response = client.get(
        "/api/v1/review-queues/advisor",
        headers=queue_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert [item["candidate"]["candidateId"] for item in payload["items"]] == [candidate_id]
    assert payload["page"]["returnedItemCount"] == 1


def test_advisor_review_queue_api_returns_bounded_page_metadata() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_ids = [
        persist_candidate(
            client,
            cash_weight=f"0.2{index}",
            suffix=f"-page-{index}",
            idempotency_key=f"seed-review-queue-page-{index}",
        )
        for index in range(3)
    ]

    first_page = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&limit=1",
        headers=queue_headers(),
    )
    snapshot_token = first_page.json()["page"]["snapshotToken"]
    response = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            f"&limit=1&offset=1&snapshotToken={snapshot_token}"
        ),
        headers=queue_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["candidate"]["candidateId"] for item in payload["items"]] == [
        sorted(candidate_ids)[1]
    ]
    assert payload["items"][0]["rank"] == 2
    assert payload["page"] | {"snapshotToken": None} == {
        "limit": 1,
        "offset": 1,
        "returnedItemCount": 1,
        "totalReviewableItemCount": 3,
        "returnedExclusionCount": 0,
        "totalExcludedCandidateCount": 0,
        "nextOffset": 2,
        "hasNextPage": True,
        "snapshotToken": None,
    }
    assert payload["page"]["snapshotToken"] == snapshot_token


def test_advisor_review_queue_api_requires_snapshot_token_for_continuation() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&offset=1",
        headers=queue_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "review_queue_snapshot_token_required"


def test_advisor_review_queue_api_rejects_malformed_snapshot_token() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            "&offset=1&snapshotToken=database-row-42"
        ),
        headers=queue_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_review_queue_snapshot_token"


def test_advisor_review_queue_api_rejects_stale_snapshot_after_backdated_insert() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-snapshot-first",
        idempotency_key="seed-review-queue-snapshot-first",
    )
    first_page = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&limit=1",
        headers=queue_headers(),
    )
    snapshot_token = first_page.json()["page"]["snapshotToken"]
    persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-snapshot-backdated",
        idempotency_key="seed-review-queue-snapshot-backdated",
    )

    response = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            f"&limit=1&offset=1&snapshotToken={snapshot_token}"
        ),
        headers=queue_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "review_queue_snapshot_conflict"


def test_advisor_review_queue_snapshot_ignores_candidates_created_after_as_of() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    visible_ids = [
        persist_candidate(
            client,
            cash_weight=f"0.2{index}",
            suffix=f"-snapshot-visible-{index}",
            idempotency_key=f"seed-review-queue-snapshot-visible-{index}",
        )
        for index in range(2)
    ]
    first_page = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&limit=1",
        headers=queue_headers(),
    )
    snapshot_token = first_page.json()["page"]["snapshotToken"]
    future_id = persist_candidate(
        client,
        cash_weight="0.29",
        suffix="-snapshot-future",
        idempotency_key="seed-review-queue-snapshot-future",
        evaluated_at_utc="2026-06-21T10:11:00Z",
    )

    second_page = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            f"&limit=1&offset=1&snapshotToken={snapshot_token}"
        ),
        headers=queue_headers(),
    )

    assert second_page.status_code == 200
    returned_ids = [item["candidate"]["candidateId"] for item in second_page.json()["items"]]
    assert returned_ids == [sorted(visible_ids)[1]]
    assert future_id not in returned_ids
    assert second_page.json()["page"]["totalReviewableItemCount"] == 2


def test_advisor_review_queue_api_rejects_page_size_above_maximum() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z&limit=101",
        headers=queue_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Request validation failed. Correct the request fields and retry.",
    }


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


def test_advisor_review_queue_api_applies_caller_entitlement_scope_without_query_filters() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    included = persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-caller-scope-included",
        idempotency_key="seed-review-queue-caller-scope-001",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
    )
    excluded = persist_candidate(
        client,
        cash_weight="0.20",
        suffix="-caller-scope-excluded",
        idempotency_key="seed-review-queue-caller-scope-002",
        candidate_scope=access_scope(portfolio_id="PB_SG_ALT_BAL_002"),
    )

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=scoped_queue_headers(),
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


def test_advisor_review_queue_api_rejects_query_scope_outside_caller_entitlements() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-scope-denied",
        idempotency_key="seed-review-queue-scope-denied-001",
        candidate_scope=access_scope(portfolio_id="PB_SG_ALT_BAL_002"),
    )

    response = client.get(
        (
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z"
            "&tenantId=tenant-private-bank-sg&bookId=book-advisor-001"
            "&portfolioId=PB_SG_ALT_BAL_002&clientId=client-001"
        ),
        headers=scoped_queue_headers(portfolio_ids="PB_SG_GLOBAL_BAL_001"),
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to read the requested advisor idea review scope.",
    }
    assert "PB_SG_ALT_BAL_002" not in response.text
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


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


def test_advisor_review_queue_api_rejects_advisor_role_without_read_capability() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Roles": "advisor",
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


def test_advisor_review_queue_api_rejects_blank_caller_scope_header_safely() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=scoped_queue_headers(portfolio_ids="PB_SG_GLOBAL_BAL_001, "),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Caller entitlement scope headers cannot contain blank values.",
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
            "invalid_state": 0,
            "suppressed": 0,
            "duplicate": 0,
            "expired": 0,
            "closed": 0,
            "rejected": 0,
            "unsupported_evidence": 0,
            "snoozed": 0,
            "unscored": 0,
            "unrankable_score_policy": 0,
            "non_reviewable_status": 0,
            "access_scope_mismatch": 0,
        },
        "scoredCandidateCount": 2,
        "unscoredCandidateCount": 0,
        "durableStorageBacked": False,
        "repositorySidePaginationCertified": False,
        "readinessStatus": "blocked",
        "supportabilityStatus": "not_certified",
        "certificationReady": False,
        "certificationBlockers": [
            "durable_repository_not_configured",
            "repository_side_queue_pagination_not_certified",
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


def test_production_profile_rejects_self_asserted_caller_context_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.delenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, raising=False)
    client = TestClient(app)

    read_response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=readiness_headers(),
    )
    mutation_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(cash_weight="0.18", suffix="-untrusted-prod"),
        headers=persist_headers("untrusted-prod-persist"),
    )

    assert read_response.status_code == 403
    assert read_response.json()["code"] == "permission_denied"
    assert mutation_response.status_code == 403
    assert mutation_response.json()["code"] == "permission_denied"


def test_production_profile_accepts_trusted_caller_context_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    client = TestClient(app)

    response = client.get(
        "/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers={
            **readiness_headers(),
            TRUSTED_CALLER_CONTEXT_HEADER: "gateway-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["readinessStatus"] == "blocked"


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
