from __future__ import annotations

from typing import Any

from tests.support.http import managed_test_client

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests


PERSISTENCE_PATH = "/api/v1/idea-signals/high-cash/evaluate-and-persist"


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


def high_cash_payload(*, tenant_suffix: str) -> dict[str, Any]:
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
        "accessScope": {
            "tenantId": f"tenant-{tenant_suffix}",
            "bookId": f"book-advisor-{tenant_suffix}",
            "portfolioId": f"PB_SG_GLOBAL_BAL_{tenant_suffix.upper()}",
            "clientId": f"client-{tenant_suffix}",
        },
        "entitlementAllowed": True,
    }


def persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": idempotency_key,
    }


def test_high_cash_persist_api_rejects_missing_scope_before_persistence() -> None:
    reset_idea_repository_for_tests()
    payload = high_cash_payload(tenant_suffix="a")
    del payload["accessScope"]

    response = managed_test_client(app).post(
        PERSISTENCE_PATH,
        json=payload,
        headers=persistence_headers("persist-high-cash-api-unscoped-001"),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Request validation failed. Correct the request fields and retry.",
    }
    snapshot = get_idea_repository().snapshot()
    assert snapshot.candidate_records == {}
    assert snapshot.idempotency_records == {}
    assert snapshot.outbox_events == {}


def test_high_cash_persist_api_isolates_business_identity_by_economic_scope() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    tenant_a = client.post(
        PERSISTENCE_PATH,
        json=high_cash_payload(tenant_suffix="a"),
        headers=persistence_headers("persist-high-cash-api-tenant-a-001"),
    )
    tenant_b = client.post(
        PERSISTENCE_PATH,
        json=high_cash_payload(tenant_suffix="b"),
        headers=persistence_headers("persist-high-cash-api-tenant-b-001"),
    )

    assert (tenant_a.status_code, tenant_b.status_code) == (200, 200)
    tenant_a_candidate = tenant_a.json()["persistence"]["candidateId"]
    tenant_b_candidate = tenant_b.json()["persistence"]["candidateId"]
    assert tenant_a_candidate != tenant_b_candidate
    assert len(get_idea_repository().snapshot().candidate_records) == 2
