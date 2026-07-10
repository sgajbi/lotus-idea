from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

from _pytest.logging import LogCaptureFixture
from fastapi.testclient import TestClient
import pytest

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, TRUSTED_CALLER_CONTEXT_TOKEN_ENV
from app.main import create_app


@dataclass(frozen=True)
class ProtectedRequest:
    method: str
    path: str
    payload: dict[str, Any] | None = None
    idempotency_key: str | None = None


PROVENANCE_CASES = (
    ProtectedRequest(
        "POST",
        "/api/v1/idea-signals/high-cash/evaluate",
        payload={
            "asOfDate": "2026-06-21",
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "sourceReportedCashWeight": "0.18",
            "sourceEvidence": {
                "portfolioStateRef": {
                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                    "sourceSystem": "lotus-core",
                    "productVersion": "v1",
                    "route": "/integration/portfolios/{portfolio_id}/core-snapshot",
                    "asOfDate": "2026-06-21",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:caller-boundary-portfolio-state",
                    "dataQualityStatus": "complete",
                    "freshness": "current",
                },
                "holdingsRef": {
                    "productId": "lotus-core:HoldingsAsOf:v1",
                    "sourceSystem": "lotus-core",
                    "productVersion": "v1",
                    "route": "/portfolios/{portfolio_id}/positions",
                    "asOfDate": "2026-06-21",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:caller-boundary-holdings",
                    "dataQualityStatus": "complete",
                    "freshness": "current",
                },
                "cashMovementRef": {
                    "productId": "lotus-core:PortfolioCashMovementSummary:v1",
                    "sourceSystem": "lotus-core",
                    "productVersion": "v1",
                    "route": "/portfolios/{portfolio_id}/cash-movement-summary",
                    "asOfDate": "2026-06-21",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:caller-boundary-cash-movement",
                    "dataQualityStatus": "complete",
                    "freshness": "current",
                },
                "cashflowProjectionRef": {
                    "productId": "lotus-core:PortfolioCashflowProjection:v1",
                    "sourceSystem": "lotus-core",
                    "productVersion": "v1",
                    "route": "/portfolios/{portfolio_id}/cashflow-projection",
                    "asOfDate": "2026-06-21",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:caller-boundary-cashflow",
                    "dataQualityStatus": "complete",
                    "freshness": "current",
                },
            },
        },
    ),
    ProtectedRequest(
        "POST",
        "/api/v1/idea-candidates/idea-boundary/lifecycle-transitions",
        payload={
            "transitionId": "transition-boundary",
            "targetLifecycleStatus": "ready_for_review",
            "changedAtUtc": "2026-06-21T10:01:00Z",
            "reasonCodes": ["review_required"],
        },
        idempotency_key="caller-boundary-lifecycle",
    ),
    ProtectedRequest("GET", "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:00:00Z"),
    ProtectedRequest("GET", "/api/v1/ai-explanations/readiness"),
    ProtectedRequest(
        "POST",
        "/api/v1/conversion-intents/conversion-boundary/report-evidence-packs",
        payload={
            "reportEvidencePackId": "report-boundary",
            "purpose": "client_review_report_section",
            "reasonCodes": ["review_approved_for_conversion"],
            "requestedAtUtc": "2026-06-21T10:02:00Z",
            "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
            "clientReadyPublicationRequested": False,
        },
        idempotency_key="caller-boundary-report",
    ),
    ProtectedRequest("GET", "/api/v1/downstream-realization/readiness"),
    ProtectedRequest(
        "GET",
        "/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:00:00Z",
    ),
)

MALFORMED_SCOPE_CASES = (
    PROVENANCE_CASES[0],
    PROVENANCE_CASES[2],
    ProtectedRequest("GET", "/api/v1/idea-candidates/idea-boundary"),
)


@pytest.mark.parametrize("case", MALFORMED_SCOPE_CASES, ids=lambda case: case.path)
def test_caller_context_boundary_preserves_invalid_scope_problem(case: ProtectedRequest) -> None:
    response = _request(
        TestClient(create_app()),
        case,
        headers={**_caller_headers(), "X-Caller-Tenant-Ids": "tenant-sensitive, "},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Correlation-Id"] == "corr-caller-boundary"
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Caller entitlement scope headers cannot contain blank values.",
    }
    assert "tenant-sensitive" not in response.text


@pytest.mark.parametrize("case", PROVENANCE_CASES, ids=lambda case: case.path)
def test_caller_context_boundary_preserves_permission_problem_across_routes(
    monkeypatch: pytest.MonkeyPatch,
    case: ProtectedRequest,
) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "trusted-gateway-secret")
    response = _request(
        TestClient(create_app()),
        case,
        headers={
            **_caller_headers(),
            TRUSTED_CALLER_CONTEXT_HEADER: "untrusted-override-secret",
        },
    )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Correlation-Id"] == "corr-caller-boundary"
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "Trusted caller context provenance is required.",
    }
    assert "trusted-gateway-secret" not in response.text
    assert "untrusted-override-secret" not in response.text


def test_caller_context_boundary_logs_safe_specific_category(
    monkeypatch: pytest.MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "trusted-gateway-secret")
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        response = _request(
            TestClient(create_app()),
            PROVENANCE_CASES[0],
            headers={
                **_caller_headers(),
                "X-Caller-Portfolio-Ids": "PB_SENSITIVE_DO_NOT_LOG",
                TRUSTED_CALLER_CONTEXT_HEADER: "untrusted-override-secret",
            },
        )

    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "lotus-idea" and record.message.startswith("{")
    ]
    boundary_event = next(event for event in events if event.get("event") == "request.http_error")
    assert response.status_code == 403
    assert boundary_event["route"] == "/api/v1/idea-signals/high-cash/evaluate"
    assert boundary_event["status_code"] == 403
    assert boundary_event["error_category"] == "caller_context_permission_denied"
    rendered = json.dumps(events)
    assert "PB_SENSITIVE_DO_NOT_LOG" not in rendered
    assert "trusted-gateway-secret" not in rendered
    assert "untrusted-override-secret" not in rendered


def _caller_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "caller-boundary-subject",
        "X-Caller-Roles": "advisor,operator",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-caller-boundary",
        "X-Trace-Id": "trace-caller-boundary",
    }


def _request(
    client: TestClient,
    case: ProtectedRequest,
    *,
    headers: dict[str, str],
):
    request_headers = dict(headers)
    if case.idempotency_key is not None:
        request_headers["Idempotency-Key"] = case.idempotency_key
    return client.request(
        case.method,
        case.path,
        json=case.payload,
        headers=request_headers,
    )
