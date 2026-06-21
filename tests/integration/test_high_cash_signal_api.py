from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

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


def high_cash_payload(
    *,
    freshness: str = "current",
    entitlement_allowed: bool = True,
    cash_weight: str | None = "0.18",
) -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": cash_weight,
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1", freshness),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness),
            "cashflowProjectionRef": source_ref(
                "lotus-core:PortfolioCashflowProjection:v1", freshness
            ),
        },
        "entitlementAllowed": entitlement_allowed,
    }


def authorized_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-high-cash-api",
    }


def test_high_cash_api_creates_candidate_from_source_owned_evidence() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-high-cash-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["family"] == "high_cash"
    assert payload["candidate"]["scorePolicyVersion"] == "idle-liquidity-v1"
    assert payload["candidate"]["sourceRefs"][0] == {
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_high_cash_api_returns_blocked_posture_for_source_entitlement_denial() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(entitlement_allowed=False),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["entitlement_denied"]
    assert payload["supportedFeaturePromoted"] is False


def test_high_cash_api_returns_blocked_posture_for_stale_source_evidence() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(freshness="stale"),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["stale_source"]


def test_high_cash_api_requires_signal_evaluation_capability() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(),
        headers={"X-Caller-Subject": "advisor-001", "X-Caller-Roles": "viewer"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }


def test_high_cash_api_validation_error_is_product_safe() -> None:
    client = TestClient(app)
    payload = high_cash_payload(cash_weight="1.1")

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 400
    body = response.text.lower()
    assert "invalid_request" in body
    assert "1.1" not in body
    assert "source/" not in body
