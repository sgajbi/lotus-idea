from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_allocation_drift_signal_api_returns_pm_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=allocation_drift_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "allocation_drift"
    assert payload["reasonCodes"] == ["allocation_drift_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-manage"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "pm_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "allocation-drift-mandate-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-manage:PortfolioActionRegister:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_allocation_drift_signal_api_reports_below_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = allocation_drift_payload()
    payload["workflowDecisionCount"] = 0

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "allocation_drift",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_blocks_store_wide_manage_posture() -> None:
    client = TestClient(app)
    payload = allocation_drift_payload()
    payload["portfolioScopeConfirmed"] = False

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["missing_source"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_reports_non_ready_source_blocker() -> None:
    client = TestClient(app)
    payload = allocation_drift_payload()
    payload["manageSupportabilityState"] = "degraded"

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = allocation_drift_payload()
    payload["actionRegisterRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=allocation_drift_payload(),
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
        "X-Caller-Subject": "pm-001",
        "X-Caller-Roles": "portfolio-manager",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def allocation_drift_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workflowDecisionCount": 2,
        "lineageEdgeCount": 4,
        "manageSupportabilityState": "ready",
        "portfolioScopeConfirmed": True,
        "actionRegisterRef": {
            "productId": "lotus-manage:PortfolioActionRegister:v1",
            "sourceSystem": "lotus-manage",
            "productVersion": "v1",
            "route": "/api/v1/rebalance/supportability/summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:portfolio-action-register",
            "dataQualityStatus": "ready",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
