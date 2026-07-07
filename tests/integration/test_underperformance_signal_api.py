from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import app.api.underperformance_signals as underperformance_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.performance_sources import (
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    PerformanceUnderperformanceSourceRuntime,
    PerformanceUnderperformanceSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingPerformanceUnderperformanceSource:
    seen_request: PerformanceUnderperformanceEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0

    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _performance_underperformance_evidence()

    def close(self) -> None:
        self.close_count += 1


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


def test_underperformance_signal_api_rejects_wrong_source_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = TestClient(app)
    payload = underperformance_payload()
    payload["performanceRef"] = {
        **payload["performanceRef"],
        "sourceSystem": "lotus-core",
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        "contentHash": "sha256:wrong-underperformance-source",
    }
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

    monkeypatch.setattr(underperformance_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "PortfolioStateSnapshot" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-performance",
            "source_ref_contract_mismatch",
        )
    ]


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


def test_underperformance_signal_from_source_api_returns_review_candidate(
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    performance_source = RecordingPerformanceUnderperformanceSource()
    monkeypatch.setattr(
        underperformance_api,
        "_build_performance_underperformance_source_runtime_from_environment",
        lambda: PerformanceUnderperformanceSourceRuntime(
            performance_source=performance_source,
            performance_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate-from-source",
        json=underperformance_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "underperformance"
    assert payload["sourceAuthority"] == "lotus-performance"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["scorePolicyVersion"] == "underperformance-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-performance:ReturnsSeriesBundle:v1"
    }
    assert performance_source.seen_request == PerformanceUnderperformanceEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=EVALUATED_AT,
        active_return_threshold=Decimal("-0.005"),
        reporting_currency="USD",
        correlation_id="corr-performance-underperformance-source-api",
        trace_id="trace-performance-underperformance-source-api",
    )
    assert performance_source.close_count == 1


def test_underperformance_signal_from_source_blocks_when_runtime_not_configured(
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        underperformance_api,
        "_build_performance_underperformance_source_runtime_from_environment",
        lambda: PerformanceUnderperformanceSourceRuntimeBlocker(
            "lotus_performance_base_url_not_configured"
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate-from-source",
        json=underperformance_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": (
            "Performance source runtime is not configured for underperformance source evaluation."
        ),
    }
    assert PORTFOLIO_ID not in response.text


def test_underperformance_signal_from_source_checks_scope_before_runtime(
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)

    def fail_if_called() -> PerformanceUnderperformanceSourceRuntimeBlocker:
        raise AssertionError("runtime must not be built when caller scope is denied")

    monkeypatch.setattr(
        underperformance_api,
        "_build_performance_underperformance_source_runtime_from_environment",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate-from-source",
        json=underperformance_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert PORTFOLIO_ID not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_underperformance_signal_from_source_closes_runtime_on_source_blocker(
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    performance_source = RecordingPerformanceUnderperformanceSource(
        error=PerformanceSourceUnavailable(code="performance_source_unavailable")
    )
    monkeypatch.setattr(
        underperformance_api,
        "_build_performance_underperformance_source_runtime_from_environment",
        lambda: PerformanceUnderperformanceSourceRuntime(
            performance_source=performance_source,
            performance_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/underperformance/evaluate-from-source",
        json=underperformance_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "underperformance",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_unavailable"],
        "candidate": None,
        "sourceAuthority": "lotus-performance",
        "supportedFeaturePromoted": False,
    }
    assert performance_source.close_count == 1


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def source_evaluation_headers(*, portfolio_ids: str = PORTFOLIO_ID) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-performance-underperformance-source-api",
        "X-Trace-Id": "trace-performance-underperformance-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
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


def underperformance_source_payload(*, portfolio_id: str = PORTFOLIO_ID) -> dict[str, str]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "periodName": "YTD",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "reportingCurrency": "usd",
    }


def _performance_underperformance_evidence() -> PerformanceUnderperformanceEvidence:
    return PerformanceUnderperformanceEvidence(
        source_reported_active_return=Decimal("-0.0125"),
        benchmark_context_available=True,
        performance_ref=SourceRef(
            product_id="lotus-performance:ReturnsSeriesBundle:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            product_version="v1",
            route="/integration/returns/series",
            as_of_date=AS_OF_DATE,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:returns-series-bundle",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        performance_diagnostic="performance_underperformance_source_ready",
    )
