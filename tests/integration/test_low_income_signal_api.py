from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_low_income_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=low_income_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "low_income"
    assert payload["reasonCodes"] == ["income_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "cashflow-liquidity-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_low_income_signal_api_reports_above_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = low_income_payload()
    payload["sourceReportedMinProjectedCumulativeCashflow"] = "-500"

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "low_income",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_low_income_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = low_income_payload()
    payload["cashflowProjectionRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "low_income",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_low_income_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=low_income_payload(),
        headers={
            "X-Caller-Subject": "viewer-001",
            "X-Caller-Roles": "viewer",
            "X-Caller-Capabilities": "idea.review.queue.read",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def low_income_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedMinProjectedCumulativeCashflow": "-12500",
        "cashMovementCount": 4,
        "cashMovementRef": {
            "productId": "lotus-core:PortfolioCashMovementSummary:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/cash-movement-summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:low-income-cash-movement",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "cashflowProjectionRef": {
            "productId": "lotus-core:PortfolioCashflowProjection:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/cashflow-projection",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:low-income-cashflow-projection",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
