from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_mandate_restriction_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/mandate-restriction/evaluate",
        json=mandate_restriction_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "mandate_restriction"
    assert payload["reasonCodes"] == ["mandate_restriction_review", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "compliance_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_mandate_restriction_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = mandate_restriction_payload()
    payload["restrictionRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/mandate-restriction/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "mandate_restriction",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-advise",
        "supportedFeaturePromoted": False,
    }


def test_mandate_restriction_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/mandate-restriction/evaluate",
        json=mandate_restriction_payload(),
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


def mandate_restriction_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "restrictionRef": {
            "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "sourceSystem": "lotus-advise",
            "productVersion": "v1",
            "route": "/advisory/policy-evaluations/pev_001/restriction-posture",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:mandate-restriction-review",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "restrictionStatus": "REVIEW_REQUIRED",
        "changedSinceLastReview": True,
        "actionabilityBlocked": True,
        "entitlementAllowed": True,
    }
