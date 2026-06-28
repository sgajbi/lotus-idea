from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_missing_benchmark_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=missing_benchmark_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_benchmark"
    assert payload["reasonCodes"] == ["missing_benchmark", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-core:BenchmarkAssignment:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_missing_benchmark_signal_api_reports_ready_assignment_not_eligible() -> None:
    client = TestClient(app)
    payload = missing_benchmark_payload()
    payload["benchmarkIdentityResolved"] = True
    payload["assignmentEffectiveForAsOfDate"] = True
    payload["assignmentStatus"] = "ACTIVE"
    payload["assignmentVersionPresent"] = True

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "missing_benchmark",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_missing_benchmark_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = missing_benchmark_payload()
    payload["benchmarkAssignmentRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_benchmark",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_missing_benchmark_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=missing_benchmark_payload(),
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


def missing_benchmark_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "benchmarkAssignmentRef": {
            "productId": "lotus-core:BenchmarkAssignment:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/benchmark-assignment",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:benchmark-assignment-gap",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "benchmarkIdentityResolved": False,
        "assignmentEffectiveForAsOfDate": False,
        "assignmentStatus": "ACTIVE",
        "assignmentVersionPresent": True,
        "entitlementAllowed": True,
    }
