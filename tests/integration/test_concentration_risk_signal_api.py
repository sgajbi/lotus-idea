from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import app.api.concentration_risk_signals as concentration_risk_api
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


def test_concentration_risk_signal_api_rejects_wrong_source_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    payload = concentration_payload()
    payload["concentrationRef"]["sourceSystem"] = "lotus-core"
    payload["concentrationRef"]["productId"] = "lotus-core:PortfolioStateSnapshot:v1"
    events: list[tuple[str, str, str, str | None]] = []

    def capture(operation: Any, outcome: Any, **kwargs: Any) -> None:
        events.append(
            (
                operation.value,
                outcome.value,
                kwargs["source_authority"],
                kwargs.get("error_code"),
            )
        )

    monkeypatch.setattr(concentration_risk_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "lotus-core:PortfolioStateSnapshot:v1" not in response.text
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-risk",
            "source_ref_contract_mismatch",
        )
    ]


def test_concentration_risk_signal_api_rejects_wrong_risk_product_id() -> None:
    client = TestClient(app)
    payload = concentration_payload()
    payload["concentrationRef"]["productId"] = "lotus-risk:RiskMetricsReport:v1"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text


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


def test_concentration_risk_signal_api_rejects_out_of_scope_access_scope() -> None:
    client = TestClient(app)
    headers = evaluate_headers()
    headers["X-Caller-Portfolio-Ids"] = "PB_SG_OTHER_002"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals for the requested scope.",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_concentration_risk_signal_api_rejects_blank_entitlement_scope_header() -> None:
    client = TestClient(app)
    headers = evaluate_headers()
    headers["X-Caller-Portfolio-Ids"] = "PB_SG_GLOBAL_BAL_001, "

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "request_rejected",
        "title": "Request rejected",
        "detail": "The service rejected the request. Correct the request or contact support with the correlation id.",
    }


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
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
        "accessScope": {
            "tenantId": "tenant-private-bank-sg",
            "bookId": "book-advisor-001",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
        "entitlementAllowed": True,
    }
