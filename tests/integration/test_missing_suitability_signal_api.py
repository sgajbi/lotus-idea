from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_missing_suitability_signal_api_returns_compliance_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=missing_suitability_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_suitability_context"
    assert payload["reasonCodes"] == ["suitability_context_missing", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "compliance_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_missing_suitability_signal_api_reports_uncertified_publication_blocker() -> None:
    client = TestClient(app)
    payload = missing_suitability_payload()
    payload["clientReadyPublication"] = "READY"

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_suitability_context",
        "reasonCodes": ["review_required"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-advise",
        "supportedFeaturePromoted": False,
    }


def test_missing_suitability_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=missing_suitability_payload(),
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


def missing_suitability_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "policyRef": {
            "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "sourceSystem": "lotus-advise",
            "productVersion": "v1",
            "route": "/advisory/policy-evaluations/pev_001/workflow",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:missing-suitability-context-review",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "evaluationStatus": "PENDING_REVIEW",
        "openRequirementCount": 2,
        "blockedRequirementCount": 0,
        "signOffStatus": "PENDING_REVIEW",
        "signOffBlockerCount": 1,
        "clientReadyPublication": "BLOCKED",
        "entitlementAllowed": True,
    }
