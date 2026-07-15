from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from tests.support.http import managed_test_client
import pytest
from pytest import MonkeyPatch

import app.api.allocation_drift_signals as allocation_drift_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceUnavailable,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    ManageMandateHealthSourceRuntime,
    ManageMandateHealthSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingManageMandateHealthSource:
    seen_request: ManageMandateHealthEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0

    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> ManageMandateHealthEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _manage_mandate_health_evidence()

    def close(self) -> None:
        self.close_count += 1


def test_allocation_drift_signal_api_returns_pm_review_candidate() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=allocation_drift_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "allocation_drift"
    assert payload["reasonCodes"] == ["allocation_drift_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-manage"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "pm_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "allocation-drift-mandate-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-manage:PortfolioActionRegister:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_allocation_drift_signal_api_reports_below_threshold_not_eligible() -> None:
    client = managed_test_client(app)
    payload = allocation_drift_payload()
    payload["workflowDecisionCount"] = 0

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "allocation_drift",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_blocks_store_wide_manage_posture() -> None:
    client = managed_test_client(app)
    payload = allocation_drift_payload()
    payload["portfolioScopeConfirmed"] = False

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["missing_source"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_reports_non_ready_source_blocker() -> None:
    client = managed_test_client(app)
    payload = allocation_drift_payload()
    payload["manageSupportabilityState"] = "degraded"

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


def test_allocation_drift_signal_api_reports_stale_source_blocker() -> None:
    client = managed_test_client(app)
    payload = allocation_drift_payload()
    payload["actionRegisterRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }


@pytest.mark.parametrize(
    ("field_name", "source_system", "product_id", "expected_source_authority"),
    (
        (
            "actionRegisterRef",
            "lotus-core",
            "lotus-core:PortfolioStateSnapshot:v1",
            "lotus-manage",
        ),
        (
            "mandatePerformanceHealthRef",
            "lotus-core",
            "lotus-core:PortfolioStateSnapshot:v1",
            "lotus-performance",
        ),
        (
            "mandateRiskHealthRef",
            "lotus-performance",
            "lotus-performance:ReturnsSeriesBundle:v1",
            "lotus-risk",
        ),
    ),
)
def test_allocation_drift_signal_api_rejects_wrong_source_contract(
    monkeypatch: MonkeyPatch,
    field_name: str,
    source_system: str,
    product_id: str,
    expected_source_authority: str,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = allocation_drift_payload()
    payload[field_name] = source_ref_payload(
        product_id=product_id,
        source_system=source_system,
    )
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

    monkeypatch.setattr(allocation_drift_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "PortfolioStateSnapshot" not in response.text
    assert "ReturnsSeriesBundle" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            expected_source_authority,
            "source_ref_contract_mismatch",
        )
    ]


def test_allocation_drift_signal_api_requires_signal_permission() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate",
        json=allocation_drift_payload(),
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


def test_allocation_drift_signal_from_source_api_returns_pm_review_candidate(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    manage_source = RecordingManageMandateHealthSource()
    monkeypatch.setattr(
        allocation_drift_api,
        "_build_manage_mandate_health_source_runtime_from_environment",
        lambda: ManageMandateHealthSourceRuntime(
            manage_source=manage_source,
            manage_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
        json=allocation_drift_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "allocation_drift"
    assert payload["sourceAuthority"] == "lotus-manage"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["scorePolicyVersion"] == "allocation-drift-mandate-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-manage:PortfolioActionRegister:v1",
        "lotus-performance:MandatePerformanceHealthContext:v1",
        "lotus-risk:MandateRiskHealthContext:v1",
    }
    assert manage_source.seen_request == ManageMandateHealthEvidenceRequest(
        tenant_id="tenant-a",
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-manage-allocation-source-api",
        trace_id="trace-manage-allocation-source-api",
    )
    assert manage_source.close_count == 1


def test_allocation_drift_signal_from_source_blocks_when_runtime_not_configured(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    monkeypatch.setattr(
        allocation_drift_api,
        "_build_manage_mandate_health_source_runtime_from_environment",
        lambda: ManageMandateHealthSourceRuntimeBlocker("lotus_manage_base_url_not_configured"),
    )

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
        json=allocation_drift_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Manage source runtime is not configured for allocation-drift source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text


def test_allocation_drift_signal_from_source_checks_scope_before_runtime(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)

    def fail_if_called() -> ManageMandateHealthSourceRuntimeBlocker:
        raise AssertionError("runtime must not be built when caller scope is denied")

    monkeypatch.setattr(
        allocation_drift_api,
        "_build_manage_mandate_health_source_runtime_from_environment",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
        json=allocation_drift_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert PORTFOLIO_ID not in response.text
    assert "PB_SG_OTHER_002" not in response.text


@pytest.mark.parametrize("tenant_ids", [None, "tenant-a,tenant-b"])
def test_allocation_drift_signal_from_source_requires_one_trusted_tenant_before_runtime(
    monkeypatch: MonkeyPatch,
    tenant_ids: str | None,
) -> None:
    client = managed_test_client(app)

    def fail_if_called() -> ManageMandateHealthSourceRuntimeBlocker:
        raise AssertionError("runtime must not be built without one trusted tenant")

    monkeypatch.setattr(
        allocation_drift_api,
        "_build_manage_mandate_health_source_runtime_from_environment",
        fail_if_called,
    )
    headers = source_evaluation_headers(tenant_ids=tenant_ids)

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
        json=allocation_drift_source_payload(),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "A single trusted tenant context is required for this source evaluation.",
    }
    assert "tenant-a" not in response.text
    assert "tenant-b" not in response.text


def test_allocation_drift_signal_from_source_closes_runtime_on_source_blocker(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    manage_source = RecordingManageMandateHealthSource(
        error=ManageSourceUnavailable(code="manage_source_unavailable")
    )
    monkeypatch.setattr(
        allocation_drift_api,
        "_build_manage_mandate_health_source_runtime_from_environment",
        lambda: ManageMandateHealthSourceRuntime(
            manage_source=manage_source,
            manage_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
        json=allocation_drift_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "allocation_drift",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_unavailable"],
        "candidate": None,
        "sourceAuthority": "lotus-manage",
        "supportedFeaturePromoted": False,
    }
    assert manage_source.close_count == 1


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def source_evaluation_headers(
    *, portfolio_ids: str = PORTFOLIO_ID, tenant_ids: str | None = "tenant-a"
) -> dict[str, str]:
    headers = {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-manage-allocation-source-api",
        "X-Trace-Id": "trace-manage-allocation-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
    }
    if tenant_ids is not None:
        headers["X-Caller-Tenant-Ids"] = tenant_ids
    return headers


def allocation_drift_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workflowDecisionCount": 2,
        "lineageEdgeCount": 4,
        "manageSupportabilityState": "ready",
        "portfolioScopeConfirmed": True,
        "actionRegisterRef": {
            "productId": "lotus-manage:PortfolioActionRegister:v1",
            "sourceSystem": "lotus-manage",
            "productVersion": "v1",
            "route": "/api/v1/rebalance/supportability/summary",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:portfolio-action-register",
            "dataQualityStatus": "ready",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }


def source_ref_payload(
    *,
    product_id: str,
    source_system: str,
) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": source_system,
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "ready",
        "freshness": "current",
    }


def allocation_drift_source_payload(*, portfolio_id: str = PORTFOLIO_ID) -> dict[str, str]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
    }


def _manage_mandate_health_evidence() -> ManageMandateHealthEvidence:
    return ManageMandateHealthEvidence(
        workflow_decision_count=2,
        lineage_edge_count=4,
        supportability_state="ready",
        supportability_reason="supportability_summary_ready",
        freshness_bucket="current",
        portfolio_scope_confirmed=True,
        action_register_ref=_source_ref(),
        mandate_performance_health_ref=_source_ref(
            product_id="lotus-performance:MandatePerformanceHealthContext:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            content_hash="sha256:mandate-performance-health",
        ),
        mandate_risk_health_ref=_source_ref(
            product_id="lotus-risk:MandateRiskHealthContext:v1",
            source_system=SourceSystem.LOTUS_RISK,
            content_hash="sha256:mandate-risk-health",
        ),
        manage_diagnostic="manage_action_register_ready_portfolio_scope",
    )


def _source_ref(
    *,
    product_id: str = "lotus-manage:PortfolioActionRegister:v1",
    source_system: SourceSystem = SourceSystem.LOTUS_MANAGE,
    content_hash: str = "sha256:portfolio-action-register",
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version="v1",
        route="/api/v1/rebalance/supportability/summary",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=content_hash,
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
