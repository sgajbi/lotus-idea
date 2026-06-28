from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_concentration_risk_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "concentration"
    assert payload["reasonCodes"] == ["concentration_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "concentration-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:ConcentrationRiskReport:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_concentration_risk_signal_api_reports_below_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = concentration_payload()
    payload["topPositionWeightCurrent"] = "0.05"
    payload["topIssuerWeightCurrent"] = "0.08"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "concentration",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_reports_partial_issuer_coverage_blocker() -> None:
    client = TestClient(app)
    payload = concentration_payload()
    payload["issuerCoverageStatus"] = "partial"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "concentration",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = concentration_payload()
    payload["concentrationRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "concentration",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
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


def concentration_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "topPositionWeightCurrent": "0.18",
        "topIssuerWeightCurrent": "0.24",
        "issuerCoverageStatus": "complete",
        "concentrationRef": {
            "productId": "lotus-risk:ConcentrationRiskReport:v1",
            "sourceSystem": "lotus-risk",
            "productVersion": "v1",
            "route": "/analytics/risk/concentration",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:concentration-risk-report",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
