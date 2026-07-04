from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_underperformance_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=underperformance_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "underperformance"
    assert payload["reasonCodes"] == ["underperformance_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-performance"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "underperformance-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-performance:ReturnsSeriesBundle:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_underperformance_signal_api_reports_above_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = underperformance_payload()
    payload["sourceReportedActiveReturn"] = "-0.001"

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "underperformance",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-performance",
        "supportedFeaturePromoted": False,
    }


def test_underperformance_signal_api_reports_missing_benchmark_context_blocker() -> None:
    client = TestClient(app)
    payload = underperformance_payload()
    payload["benchmarkContextAvailable"] = False

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "underperformance",
        "reasonCodes": ["missing_benchmark"],
        "unsupportedReasons": ["missing_source"],
        "candidate": None,
        "sourceAuthority": "lotus-performance",
        "supportedFeaturePromoted": False,
    }


def test_underperformance_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = underperformance_payload()
    payload["performanceRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "underperformance",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-performance",
        "supportedFeaturePromoted": False,
    }


def test_underperformance_signal_api_rejects_non_performance_source_ref() -> None:
    client = TestClient(app)
    payload = underperformance_payload()
    payload["performanceRef"]["sourceSystem"] = "lotus-core"
    payload["performanceRef"]["productId"] = "lotus-core:PortfolioStateSnapshot:v1"

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text


def test_underperformance_signal_api_rejects_wrong_performance_product_id() -> None:
    client = TestClient(app)
    payload = underperformance_payload()
    payload["performanceRef"]["productId"] = "lotus-performance:MandatePerformanceHealthContext:v1"

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text


def test_underperformance_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=underperformance_payload(),
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


def underperformance_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedActiveReturn": "-0.0125",
        "benchmarkContextAvailable": True,
        "performanceRef": {
            "productId": "lotus-performance:ReturnsSeriesBundle:v1",
            "sourceSystem": "lotus-performance",
            "productVersion": "v1",
            "route": "/integration/returns/series",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:returns-series-bundle",
            "dataQualityStatus": "ready",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }
