from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.low_income_signals as low_income_signals_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceUnavailable,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    CoreLowIncomeSourceRuntime,
    CoreLowIncomeSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreLowIncomeSource(CoreLowIncomeSourcePort):
    seen_request: CoreLowIncomeEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0
    close_error: Exception | None = None

    def fetch_low_income_evidence(
        self,
        request: CoreLowIncomeEvidenceRequest,
    ) -> CoreLowIncomeEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _core_low_income_evidence()

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


def test_low_income_source_api_fetches_core_evidence_without_persistence(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    source = RecordingCoreLowIncomeSource()
    runtime = CoreLowIncomeSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-low-income-source-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    }
    assert source.seen_request == CoreLowIncomeEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        horizon_days=30,
        correlation_id="corr-low-income-source-api",
        trace_id="trace-low-income-source-api",
    )
    assert source.close_count == 1
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert "route" not in response.text
    assert "contentHash" not in response.text


def test_low_income_source_api_requires_portfolio_entitlement(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreLowIncomeSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built after entitlement denial")

    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        fail_if_called,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_OTHER"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False
    assert PORTFOLIO_ID not in response.text


def test_low_income_source_api_blocks_when_core_runtime_is_not_configured(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        lambda: CoreLowIncomeSourceRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            core_base_url_configured=False,
            core_query_base_url_configured=False,
            core_query_control_plane_base_url_configured=False,
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Core source runtime is not configured for low-income source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text
    assert "lotus_core_base_url_not_configured" not in response.text


def test_low_income_source_api_returns_blocked_posture_for_core_unavailable(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreLowIncomeSource(error=CoreSourceUnavailable(code="core_query_pending"))
    runtime = CoreLowIncomeSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["source_unavailable"]
    assert source.close_count == 1
    assert PORTFOLIO_ID not in response.text


def test_low_income_source_api_emits_bounded_operation_events(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreLowIncomeSource()
    runtime = CoreLowIncomeSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    events: list[tuple[str, str, str, bool, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append(
            (
                args[0].value,
                args[1].value,
                kwargs["source_authority"],
                kwargs.get("durable_storage_backed", False),
                kwargs.get("error_code"),
            )
        )

    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(low_income_signals_api, "emit_foundation_operation_event", capture_event)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert events == [("signal_evaluation", "accepted", "lotus-core", False, None)]


def test_low_income_source_api_suppresses_runtime_close_failure(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreLowIncomeSource(close_error=RuntimeError(f"close {PORTFOLIO_ID}"))
    runtime = CoreLowIncomeSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    events: list[tuple[str, str, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append((args[0].value, args[1].value, kwargs.get("error_code")))

    monkeypatch.setattr(
        low_income_signals_api,
        "_build_core_low_income_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(low_income_signals_api, "emit_foundation_operation_event", capture_event)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate-from-source",
        json=low_income_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "candidate_created"
    assert source.close_count == 1
    assert ("signal_evaluation", "suppressed", "runtime_cleanup_failed") in events
    assert "close " not in response.text
    assert PORTFOLIO_ID not in response.text


def test_low_income_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=low_income_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "low_income"
    assert payload["reasonCodes"] == ["income_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "cashflow-liquidity-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_low_income_signal_api_reports_above_threshold_not_eligible() -> None:
    client = TestClient(app)
    payload = low_income_payload()
    payload["sourceReportedMinProjectedCumulativeCashflow"] = "-500"

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "low_income",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_low_income_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = low_income_payload()
    payload["cashflowProjectionRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "low_income",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


@pytest.mark.parametrize("field_name", ("cashMovementRef", "cashflowProjectionRef"))
def test_low_income_signal_api_rejects_wrong_source_contract(
    monkeypatch: Any,
    field_name: str,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = TestClient(app)
    payload = low_income_payload()
    payload[field_name] = {
        **payload[field_name],
        "productId": "lotus-risk:RiskMetricsReport:v1",
        "sourceSystem": "lotus-risk",
        "route": "/risk/reports/PB_SG_GLOBAL_BAL_001",
        "contentHash": "sha256:wrong-low-income-source",
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

    monkeypatch.setattr(low_income_signals_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "RiskMetricsReport" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-core",
            "source_ref_contract_mismatch",
        )
    ]


def test_low_income_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/low-income/evaluate",
        json=low_income_payload(),
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


def source_evaluation_headers(
    *,
    portfolio_ids: str = PORTFOLIO_ID,
) -> dict[str, str]:
    return {
        **evaluate_headers(),
        "X-Correlation-Id": "corr-low-income-source-api",
        "X-Trace-Id": "trace-low-income-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
        "X-Caller-Tenant-Ids": "tenant-a",
    }


def low_income_source_payload(
    *,
    portfolio_id: str = PORTFOLIO_ID,
) -> dict[str, Any]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "horizonDays": 30,
    }


def low_income_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedMinProjectedCumulativeCashflow": "-12500",
        "cashMovementCount": 4,
        "cashMovementRef": {
            "productId": "lotus-core:PortfolioCashMovementSummary:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/cash-movement-summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:low-income-cash-movement",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "cashflowProjectionRef": {
            "productId": "lotus-core:PortfolioCashflowProjection:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/cashflow-projection",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:low-income-cashflow-projection",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _core_low_income_evidence() -> CoreLowIncomeEvidence:
    return CoreLowIncomeEvidence(
        source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
        cash_movement_count=4,
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )
