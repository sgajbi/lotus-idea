from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest
from tests.support.http import managed_test_client

import app.api.bond_maturity_signals as bond_maturity_signals_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
    CoreSourceUnavailable,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    CoreBondMaturitySourceRuntime,
    CoreBondMaturitySourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreBondMaturitySource(CoreBondMaturitySourcePort):
    seen_request: CoreBondMaturityEvidenceRequest | None = None
    evidence: CoreBondMaturityEvidence | None = None
    error: Exception | None = None
    close_count: int = 0
    close_error: Exception | None = None

    def fetch_bond_maturity_evidence(
        self,
        request: CoreBondMaturityEvidenceRequest,
    ) -> CoreBondMaturityEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return self.evidence or _core_bond_maturity_evidence()

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


def test_bond_maturity_source_api_fetches_core_evidence_without_persistence(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    source = RecordingCoreBondMaturitySource()
    runtime = CoreBondMaturitySourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: runtime,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-bond-maturity-source-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioMaturitySummary:v1",
    }
    assert source.seen_request == CoreBondMaturityEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        maturity_window_days=45,
        correlation_id="corr-bond-maturity-source-api",
        trace_id="trace-bond-maturity-source-api",
    )
    assert source.close_count == 1
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert "route" not in response.text
    assert "contentHash" not in response.text


def test_bond_maturity_source_api_requires_portfolio_entitlement(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreBondMaturitySourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built after entitlement denial")

    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        fail_if_called,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_OTHER"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False
    assert PORTFOLIO_ID not in response.text


def test_bond_maturity_source_api_blocks_when_core_runtime_is_not_configured(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: CoreBondMaturitySourceRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            core_base_url_configured=False,
            core_query_base_url_configured=False,
            core_query_control_plane_base_url_configured=False,
        ),
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Core source runtime is not configured for bond-maturity source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text
    assert "lotus_core_base_url_not_configured" not in response.text


def test_bond_maturity_source_api_returns_blocked_posture_for_core_unavailable(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBondMaturitySource(
        error=CoreSourceUnavailable(code="core_maturity_summary_pending")
    )
    runtime = CoreBondMaturitySourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: runtime,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["source_unavailable"]
    assert source.close_count == 1
    assert PORTFOLIO_ID not in response.text


@pytest.mark.parametrize(
    ("next_maturity_date", "duplicate_of_candidate_id", "expected_outcome"),
    (
        (date(2026, 7, 10), "idea_bond_maturity_existing", "suppressed"),
        (date(2026, 8, 15), None, "not_eligible"),
    ),
)
def test_bond_maturity_source_api_exposes_non_candidate_success_modes(
    monkeypatch: Any,
    next_maturity_date: date,
    duplicate_of_candidate_id: str | None,
    expected_outcome: str,
) -> None:
    source = RecordingCoreBondMaturitySource(
        evidence=_core_bond_maturity_evidence(next_maturity_date=next_maturity_date)
    )
    runtime = CoreBondMaturitySourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: runtime,
    )
    request_payload = bond_maturity_source_payload()
    request_payload["duplicateOfCandidateId"] = duplicate_of_candidate_id

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=request_payload,
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": expected_outcome,
        "family": "bond_maturity",
        "reasonCodes": [
            "duplicate_suppressed" if expected_outcome == "suppressed" else "below_materiality"
        ],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }
    assert source.close_count == 1


def test_bond_maturity_source_api_emits_bounded_operation_events(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBondMaturitySource()
    runtime = CoreBondMaturitySourceRuntime(
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
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "emit_foundation_operation_event",
        capture_event,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert events == [("signal_evaluation", "accepted", "lotus-core", False, None)]


def test_bond_maturity_source_api_suppresses_runtime_close_failure(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBondMaturitySource(close_error=RuntimeError(f"close {PORTFOLIO_ID}"))
    runtime = CoreBondMaturitySourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    events: list[tuple[str, str, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append((args[0].value, args[1].value, kwargs.get("error_code")))

    monkeypatch.setattr(
        bond_maturity_signals_api,
        "_build_core_bond_maturity_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(
        bond_maturity_signals_api,
        "emit_foundation_operation_event",
        capture_event,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
        json=bond_maturity_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "candidate_created"
    assert source.close_count == 1
    assert ("signal_evaluation", "suppressed", "runtime_cleanup_failed") in events
    assert "close " not in response.text
    assert PORTFOLIO_ID not in response.text


def test_bond_maturity_signal_api_returns_review_candidate() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=bond_maturity_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "bond_maturity"
    assert payload["reasonCodes"] == ["maturity_window", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "bond-maturity-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioMaturitySummary:v1",
    }
    assert all("route" not in source_ref for source_ref in payload["candidate"]["sourceRefs"])
    assert all("contentHash" not in source_ref for source_ref in payload["candidate"]["sourceRefs"])


def test_bond_maturity_signal_api_reports_outside_window_not_eligible() -> None:
    client = managed_test_client(app)
    payload = bond_maturity_payload()
    payload["sourceReportedNextMaturityDate"] = "2026-08-15"

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "bond_maturity",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_bond_maturity_signal_api_reports_stale_source_blocker() -> None:
    client = managed_test_client(app)
    payload = bond_maturity_payload()
    payload["holdingsRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "bond_maturity",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_bond_maturity_signal_api_reports_duplicate_suppressed() -> None:
    payload = bond_maturity_payload()
    payload["duplicateOfCandidateId"] = "idea_bond_maturity_existing"

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "suppressed",
        "family": "bond_maturity",
        "reasonCodes": ["duplicate_suppressed"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


@pytest.mark.parametrize("field_name", ("holdingsRef", "maturityFactRef"))
def test_bond_maturity_signal_api_rejects_wrong_source_contract(
    monkeypatch: Any,
    field_name: str,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = bond_maturity_payload()
    payload[field_name] = {
        **payload[field_name],
        "productId": "lotus-risk:RiskMetricsReport:v1",
        "sourceSystem": "lotus-risk",
        "route": "/risk/reports/PB_SG_GLOBAL_BAL_001",
        "contentHash": "sha256:wrong-bond-maturity-source",
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

    monkeypatch.setattr(bond_maturity_signals_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
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


def test_bond_maturity_signal_api_requires_signal_permission() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/bond-maturity/evaluate",
        json=bond_maturity_payload(),
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
        "X-Correlation-Id": "corr-bond-maturity-source-api",
        "X-Trace-Id": "trace-bond-maturity-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
        "X-Caller-Tenant-Ids": "tenant-a",
    }


def bond_maturity_source_payload(
    *,
    portfolio_id: str = PORTFOLIO_ID,
) -> dict[str, Any]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "maturityWindowDays": 45,
    }


def bond_maturity_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedNextMaturityDate": "2026-07-10",
        "sourceReportedMaturingPositionCount": 2,
        "holdingsRef": {
            "productId": "lotus-core:HoldingsAsOf:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/positions",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:bond-maturity-holdings",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "maturityFactRef": {
            "productId": "lotus-core:PortfolioMaturitySummary:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/portfolios/PB_SG_GLOBAL_BAL_001/maturity-summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:portfolio-maturity-summary",
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


def _core_bond_maturity_evidence(
    *,
    next_maturity_date: date = date(2026, 7, 10),
) -> CoreBondMaturityEvidence:
    return CoreBondMaturityEvidence(
        source_reported_next_maturity_date=next_maturity_date,
        source_reported_maturing_position_count=2,
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
        maturity_diagnostic="core_maturity_summary_maturity_window_detected",
    )
