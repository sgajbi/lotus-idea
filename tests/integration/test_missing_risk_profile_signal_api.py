from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_missing_risk_profile_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-risk-profile/evaluate",
        json=missing_risk_profile_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_risk_profile"
    assert payload["reasonCodes"] == ["missing_risk_profile", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_missing_risk_profile_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = missing_risk_profile_payload()
    payload["riskProfileRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/missing-risk-profile/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_risk_profile",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-advise",
        "supportedFeaturePromoted": False,
    }


def test_missing_risk_profile_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-risk-profile/evaluate",
        json=missing_risk_profile_payload(),
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


def missing_risk_profile_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "riskProfileRef": {
            "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "sourceSystem": "lotus-advise",
            "productVersion": "v1",
            "route": "/advisory/policy-evaluations/pev_001/risk-profile-posture",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:missing-risk-profile-review",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "riskProfileStatus": "STALE",
        "riskProfileEffectiveForAsOfDate": False,
        "riskProfileReviewDue": True,
        "entitlementAllowed": True,
    }
