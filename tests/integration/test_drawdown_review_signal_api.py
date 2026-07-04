from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_drawdown_review_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=drawdown_review_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "high_volatility"
    assert payload["reasonCodes"] == ["drawdown_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "drawdown-review-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:DrawdownAnalyticsReport:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_drawdown_review_signal_api_reports_below_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = drawdown_review_payload()
    payload["sourceReportedMaxDrawdown"] = "-0.025"

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "high_volatility",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_drawdown_review_signal_api_reports_non_ready_source_blocker() -> None:
    client = TestClient(app)
    payload = drawdown_review_payload()
    payload["riskSupportabilityState"] = "degraded"

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "high_volatility",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_drawdown_review_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = drawdown_review_payload()
    payload["drawdownRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "high_volatility",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_drawdown_review_signal_api_rejects_non_risk_source_ref() -> None:
    client = TestClient(app)
    payload = drawdown_review_payload()
    payload["drawdownRef"]["sourceSystem"] = "lotus-core"
    payload["drawdownRef"]["productId"] = "lotus-core:PortfolioStateSnapshot:v1"

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text


def test_drawdown_review_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/drawdown-review/evaluate",
        json=drawdown_review_payload(),
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


def drawdown_review_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedMaxDrawdown": "-0.1245",
        "riskSupportabilityState": "ready",
        "drawdownRef": {
            "productId": "lotus-risk:DrawdownAnalyticsReport:v1",
            "sourceSystem": "lotus-risk",
            "productVersion": "v1",
            "route": "/analytics/risk/drawdown",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:drawdown-analytics-report",
            "dataQualityStatus": "ready",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
