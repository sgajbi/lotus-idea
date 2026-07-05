from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_bond_maturity_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=bond_maturity_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "bond_maturity"
    assert payload["reasonCodes"] == ["maturity_window", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "bond-maturity-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioMaturitySummary:v1",
    }
    assert all("route" not in source_ref for source_ref in payload["candidate"]["sourceRefs"])
    assert all("contentHash" not in source_ref for source_ref in payload["candidate"]["sourceRefs"])


def test_bond_maturity_signal_api_reports_outside_window_not_eligible() -> None:
    client = TestClient(app)
    payload = bond_maturity_payload()
    payload["sourceReportedNextMaturityDate"] = "2026-08-15"

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "bond_maturity",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_bond_maturity_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = bond_maturity_payload()
    payload["holdingsRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "bond_maturity",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_bond_maturity_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=bond_maturity_payload(),
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


def bond_maturity_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedNextMaturityDate": "2026-07-10",
        "sourceReportedMaturingPositionCount": 2,
        "holdingsRef": {
            "productId": "lotus-core:HoldingsAsOf:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/positions",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:bond-maturity-holdings",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "maturityFactRef": {
            "productId": "lotus-core:PortfolioMaturitySummary:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/maturity-summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:portfolio-maturity-summary",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
