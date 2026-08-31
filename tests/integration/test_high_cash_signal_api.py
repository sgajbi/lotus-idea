from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from tests.support.http import managed_test_client
import psycopg

import app.api.idea_signals as idea_signals_api
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, TRUSTED_CALLER_CONTEXT_TOKEN_ENV
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceUnavailable,
)
from app.runtime.repository_state import (
    DATABASE_URL_ENV,
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from app.runtime.source_ingestion_state import (
    CoreHighCashSourceRuntime,
    CoreHighCashSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


class DurableInMemoryIdeaRepository(InMemoryIdeaRepository):
    durable_storage_backed = True


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    seen_request: CoreHighCashEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0
    close_error: Exception | None = None
    evidence: CoreHighCashEvidence | None = None

    def fetch_high_cash_evidence(
        self,
        request: CoreHighCashEvidenceRequest,
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return self.evidence or _core_evidence()

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


def source_ref(product_id: str, freshness: str = "current") -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": freshness,
    }


def high_cash_payload(
    *,
    freshness: str = "current",
    entitlement_allowed: bool = True,
    cash_weight: str | None = "0.18",
    scoped: bool = False,
) -> dict[str, Any]:
    payload = {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": cash_weight,
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1", freshness),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness),
            "cashflowProjectionRef": source_ref(
                "lotus-core:PortfolioCashflowProjection:v1", freshness
            ),
        },
        "entitlementAllowed": entitlement_allowed,
    }
    if scoped:
        payload["accessScope"] = {
            "tenantId": "tenant-a",
            "bookId": "book-advisor-001",
            "portfolioId": PORTFOLIO_ID,
            "clientId": "client-001",
        }
    return payload


def authorized_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-high-cash-api",
    }


def source_evaluation_headers(
    *,
    portfolio_ids: str = PORTFOLIO_ID,
    tenant_ids: str | None = "tenant-a",
) -> dict[str, str]:
    headers = {
        **authorized_headers(),
        "X-Correlation-Id": "corr-high-cash-source-api",
        "X-Trace-Id": "trace-high-cash-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
    }
    if tenant_ids is not None:
        headers["X-Caller-Tenant-Ids"] = tenant_ids
    return headers


def high_cash_source_payload(
    *,
    portfolio_id: str = PORTFOLIO_ID,
) -> dict[str, str]:
    payload = {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
    }
    return payload


def persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-high-cash-persist-api",
        "Idempotency-Key": idempotency_key,
    }


def _capture_signal_operation_events(
    monkeypatch: Any,
) -> list[tuple[str, str, str, str | None]]:
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

    monkeypatch.setattr(idea_signals_api, "emit_foundation_operation_event", capture)
    return events


def _configured_core_runtime(source: RecordingCoreSource) -> CoreHighCashSourceRuntime:
    return CoreHighCashSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_high_cash_source_api_fetches_core_evidence_without_persistence(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests()
    source = RecordingCoreSource()
    runtime = _configured_core_runtime(source)
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-high-cash-source-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["sourceRefs"][0] == {
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert source.seen_request == CoreHighCashEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-high-cash-source-api",
        trace_id="trace-high-cash-source-api",
    )
    assert source.close_count == 1
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert "route" not in response.text
    assert "contentHash" not in response.text


def test_high_cash_source_api_reports_not_eligible(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreSource(evidence=_core_evidence(cash_weight=Decimal("0.05")))
    runtime = _configured_core_runtime(source)
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )
    client = managed_test_client(app)

    not_eligible = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )
    assert not_eligible.status_code == 200
    assert not_eligible.json()["outcome"] == "not_eligible"
    assert not_eligible.json()["reasonCodes"] == ["below_materiality"]
    assert not_eligible.json()["candidate"] is None
    assert source.close_count == 1


def test_high_cash_source_api_blocks_temporally_mismatched_adapter_evidence(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests()
    evidence = _core_evidence()
    assert evidence.holdings_ref is not None
    source = RecordingCoreSource(
        evidence=replace(
            evidence,
            holdings_ref=replace(evidence.holdings_ref, as_of_date=date(2026, 6, 20)),
        )
    )
    runtime = _configured_core_runtime(source)
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "blocked"
    assert response.json()["reasonCodes"] == ["source_date_mismatch"]
    assert response.json()["unsupportedReasons"] == ["source_temporal_mismatch"]
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert source.close_count == 1


def test_high_cash_source_api_requires_portfolio_entitlement(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreHighCashSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built after entitlement denial")

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        fail_if_called,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_OTHER"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False
    assert PORTFOLIO_ID not in response.text


def test_high_cash_source_api_requires_one_trusted_tenant_before_runtime(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreHighCashSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built without tenant context")

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        fail_if_called,
    )
    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(tenant_ids=None),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False


def test_high_cash_source_api_rejects_ambiguous_tenant_context(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreHighCashSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built with ambiguous tenant context")

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        fail_if_called,
    )
    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(tenant_ids="tenant-a,tenant-b"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False


def test_high_cash_source_api_rejects_untrusted_tenant_override_before_runtime(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreHighCashSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built for untrusted caller context")

    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        fail_if_called,
    )
    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(tenant_ids="tenant-attacker"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False
    assert "tenant-attacker" not in response.text


def test_high_cash_source_api_rejects_body_tenant_override_before_runtime(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreHighCashSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built for a body tenant override")

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        fail_if_called,
    )
    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json={**high_cash_source_payload(), "tenantId": "tenant-attacker"},
        headers=source_evaluation_headers(tenant_ids="tenant-a"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert runtime_called is False
    assert "tenant-attacker" not in response.text


def test_high_cash_source_api_blocks_when_core_runtime_is_not_configured(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: CoreHighCashSourceRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            core_base_url_configured=False,
            core_query_base_url_configured=False,
            core_query_control_plane_base_url_configured=False,
        ),
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Core source runtime is not configured for high-cash source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text
    assert "lotus_core_base_url_not_configured" not in response.text


def test_high_cash_source_api_returns_blocked_posture_for_core_unavailable(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreSource(error=CoreSourceUnavailable(code="core_query_unavailable"))
    runtime = _configured_core_runtime(source)
    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["source_unavailable"]
    assert source.close_count == 1
    assert PORTFOLIO_ID not in response.text


def test_high_cash_source_api_emits_bounded_tenant_scope_operation_event(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreSource()
    runtime = _configured_core_runtime(source)
    events: list[tuple[str, str, str, bool, str | None, dict[str, str]]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append(
            (
                args[0].value,
                args[1].value,
                kwargs["source_authority"],
                kwargs.get("durable_storage_backed", False),
                kwargs.get("error_code"),
                kwargs.get("attributes", {}),
            )
        )

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(idea_signals_api, "emit_foundation_operation_event", capture_event)
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "signal_evaluation",
            "accepted",
            "lotus-core",
            False,
            None,
            {"tenant_scope_provenance": "trusted_single_tenant"},
        )
    ]


def test_high_cash_source_api_suppresses_runtime_close_failure(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreSource(close_error=RuntimeError(f"close failed for {PORTFOLIO_ID}"))
    runtime = _configured_core_runtime(source)
    events: list[tuple[str, str, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append((args[0].value, args[1].value, kwargs.get("error_code")))

    monkeypatch.setattr(
        idea_signals_api,
        "_build_core_high_cash_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(idea_signals_api, "emit_foundation_operation_event", capture_event)
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-from-source",
        json=high_cash_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "candidate_created"
    assert source.close_count == 1
    assert ("signal_evaluation", "suppressed", "runtime_cleanup_failed") in events
    assert "close failed" not in response.text
    assert PORTFOLIO_ID not in response.text


def test_high_cash_api_creates_candidate_from_source_owned_evidence() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-high-cash-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["family"] == "high_cash"
    assert payload["candidate"]["scorePolicyVersion"] == "idle-liquidity-v2"
    assert payload["candidate"]["score"] == "82.50"
    assert [component["component"] for component in payload["candidate"]["scoreComponents"]] == [
        "materiality",
        "evidence_quality",
        "freshness",
    ]
    assert payload["candidate"]["sourceRefs"][0] == {
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_high_cash_api_reports_not_eligible() -> None:
    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(cash_weight="0.05"),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "not_eligible"
    assert response.json()["reasonCodes"] == ["below_materiality"]
    assert response.json()["candidate"] is None
    assert response.json()["supportedFeaturePromoted"] is False


def test_high_cash_api_rejects_caller_asserted_duplicate_authority() -> None:
    payload = high_cash_payload()
    payload["duplicateOfCandidateId"] = "idea_high_cash_caller_assertion"

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Request validation failed. Correct the request fields and retry.",
    }
    assert "idea_high_cash_caller_assertion" not in response.text


def test_high_cash_api_returns_blocked_posture_for_source_entitlement_denial() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(entitlement_allowed=False),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["entitlement_denied"]
    assert payload["supportedFeaturePromoted"] is False


def test_high_cash_api_blocks_mismatched_source_business_date() -> None:
    payload = high_cash_payload()
    payload["sourceEvidence"]["portfolioStateRef"]["asOfDate"] = "2026-06-20"

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["outcome"] == "blocked"
    assert response_payload["candidate"] is None
    assert response_payload["reasonCodes"] == ["source_date_mismatch"]
    assert response_payload["unsupportedReasons"] == ["source_temporal_mismatch"]


def test_high_cash_api_returns_blocked_posture_for_stale_source_evidence() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(freshness="stale"),
        headers=authorized_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["stale_source"]


def test_high_cash_api_rejects_wrong_core_product_id(monkeypatch: Any) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = high_cash_payload()
    payload["sourceEvidence"]["portfolioStateRef"]["productId"] = (
        "lotus-core:BenchmarkAssignment:v1"
    )
    events = _capture_signal_operation_events(monkeypatch)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "BenchmarkAssignment" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-core",
            "source_ref_contract_mismatch",
        )
    ]


def test_high_cash_api_rejects_non_core_source_ref(monkeypatch: Any) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = high_cash_payload()
    payload["sourceEvidence"]["portfolioStateRef"]["sourceSystem"] = "lotus-risk"
    payload["sourceEvidence"]["portfolioStateRef"]["productId"] = (
        "lotus-risk:ConcentrationRiskReport:v1"
    )
    events = _capture_signal_operation_events(monkeypatch)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "ConcentrationRiskReport" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-core",
            "source_ref_contract_mismatch",
        )
    ]


def test_high_cash_api_requires_signal_evaluation_capability() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(),
        headers={"X-Caller-Subject": "advisor-001", "X-Caller-Roles": "viewer"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }


def _source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def _core_evidence(
    *,
    cash_weight: Decimal = Decimal("0.18"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=_source_ref(
            "lotus-core:PortfolioStateSnapshot:v1",
            freshness=freshness,
        ),
        holdings_ref=_source_ref(
            "lotus-core:HoldingsAsOf:v1",
            freshness=freshness,
        ),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            freshness=freshness,
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            freshness=freshness,
        ),
    )


def test_high_cash_api_rejects_advisor_role_without_signal_evaluation_capability() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=high_cash_payload(),
        headers={"X-Caller-Subject": "advisor-001", "X-Caller-Roles": "advisor"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }
    body = response.text
    assert "PB_SG_GLOBAL_BAL_001" not in body
    assert "client-001" not in body
    assert "lotus-core:PortfolioStateSnapshot:v1" not in body


def test_high_cash_api_validation_error_is_product_safe() -> None:
    client = managed_test_client(app)
    payload = high_cash_payload(cash_weight="1.1")

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate",
        json=payload,
        headers=authorized_headers(),
    )

    assert response.status_code == 400
    body = response.text.lower()
    assert "invalid_request" in body
    assert "1.1" not in body
    assert "source/" not in body


def test_high_cash_persist_api_persists_created_candidate_with_audit_posture() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=persistence_headers("persist-high-cash-api-accepted-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-high-cash-persist-api"
    payload = response.json()
    assert payload["evaluation"]["outcome"] == "candidate_created"
    assert payload["evaluation"]["supportedFeaturePromoted"] is False
    assert payload["persistence"]["decision"] == "accepted"
    assert (
        payload["persistence"]["candidateId"] == payload["evaluation"]["candidate"]["candidateId"]
    )
    assert payload["persistence"]["auditEventType"] == "idea.candidate.persisted"
    assert payload["persistence"]["identity"]["materialVersion"] == 1
    assert payload["persistence"]["identity"]["evidenceVersion"] == 1
    assert payload["persistence"]["identity"]["changeReason"] == "initial_detection"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def test_high_cash_persist_api_rejects_missing_scope_before_persistence() -> None:
    reset_idea_repository_for_tests()
    payload = high_cash_payload(scoped=True)
    del payload["accessScope"]

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=persistence_headers("persist-high-cash-api-unscoped-001"),
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Request validation failed. Correct the request fields and retry.",
    }
    snapshot = get_idea_repository().snapshot()
    assert snapshot.candidate_records == {}
    assert snapshot.idempotency_records == {}
    assert snapshot.outbox_events == {}


def test_high_cash_persist_api_isolates_business_identity_by_economic_scope() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    tenant_a_payload = high_cash_payload(scoped=True)
    tenant_b_payload = high_cash_payload(scoped=True)
    tenant_b_payload["accessScope"] = {
        "tenantId": "tenant-b",
        "bookId": "book-advisor-002",
        "portfolioId": "PB_SG_GLOBAL_BAL_002",
        "clientId": "client-002",
    }

    tenant_a = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_a_payload,
        headers=persistence_headers("persist-high-cash-api-tenant-a-001"),
    )
    tenant_b = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_b_payload,
        headers=persistence_headers("persist-high-cash-api-tenant-b-001"),
    )

    assert (tenant_a.status_code, tenant_b.status_code) == (200, 200)
    tenant_a_candidate = tenant_a.json()["persistence"]["candidateId"]
    tenant_b_candidate = tenant_b.json()["persistence"]["candidateId"]
    assert tenant_a_candidate != tenant_b_candidate
    assert len(get_idea_repository().snapshot().candidate_records) == 2


def test_high_cash_persist_api_rejects_unsafe_causation_before_persistence() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    headers = persistence_headers("persist-high-cash-api-unsafe-causation-001")
    headers["X-Causation-Id"] = "bearer-secret-token"

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Correct the event lineage headers and retry.",
    }
    assert "bearer-secret-token" not in response.text
    assert get_idea_repository().snapshot().candidate_records == {}


def test_high_cash_persist_api_rejects_wrong_source_contract_before_persistence() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    payload = high_cash_payload(scoped=True)
    payload["sourceEvidence"]["portfolioStateRef"]["sourceSystem"] = "lotus-risk"
    payload["sourceEvidence"]["portfolioStateRef"]["productId"] = (
        "lotus-risk:ConcentrationRiskReport:v1"
    )

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=persistence_headers("persist-high-cash-api-wrong-source-001"),
    )

    repository = get_idea_repository()
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert len(repository.snapshot().candidate_records) == 0
    assert "lotus-risk:ConcentrationRiskReport:v1" not in response.text


def test_high_cash_persist_api_reports_durable_storage_when_repository_is_durable() -> None:
    reset_idea_repository_for_tests(DurableInMemoryIdeaRepository())
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=persistence_headers("persist-high-cash-api-durable-001"),
    )

    assert response.status_code == 200
    assert response.json()["durableStorageBacked"] is True


def test_high_cash_persist_api_fails_closed_when_durable_repository_is_required(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    reset_idea_repository_for_tests(reload_from_environment=True)
    client = managed_test_client(app)

    try:
        response = client.post(
            "/api/v1/idea-signals/high-cash/evaluate-and-persist",
            json=high_cash_payload(scoped=True),
            headers={
                **persistence_headers("persist-high-cash-api-prod-missing-db-001"),
                TRUSTED_CALLER_CONTEXT_HEADER: "gateway-secret",
            },
        )
        repository = get_idea_repository()
    finally:
        reset_idea_repository_for_tests()

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "durable_repository_not_configured",
        "title": "Durable repository not configured",
        "detail": (
            "This runtime profile requires LOTUS_IDEA_DATABASE_URL before "
            "write-capable idea operations can run."
        ),
    }
    assert len(repository.snapshot().candidate_records) == 0


def test_high_cash_persist_api_fails_closed_when_durable_repository_unavailable(
    monkeypatch: Any,
) -> None:
    def fake_connect(database_url: str, *, row_factory: object) -> object:
        raise psycopg.OperationalError(
            "could not connect to db.internal.example with password secret"
        )

    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "gateway-secret")
    monkeypatch.setenv(
        DATABASE_URL_ENV,
        "postgresql://lotus_idea:secret@db.internal.example:5432/lotus_idea",
    )
    monkeypatch.setattr("app.runtime.repository_state.psycopg.connect", fake_connect)
    reset_idea_repository_for_tests(reload_from_environment=True)
    client = managed_test_client(app, raise_server_exceptions=False)

    try:
        response = client.post(
            "/api/v1/idea-signals/high-cash/evaluate-and-persist",
            json=high_cash_payload(scoped=True),
            headers={
                **persistence_headers("persist-high-cash-api-prod-unavailable-db-001"),
                TRUSTED_CALLER_CONTEXT_HEADER: "gateway-secret",
            },
        )
        repository = get_idea_repository()
    finally:
        reset_idea_repository_for_tests()

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "durable_repository_unavailable",
        "title": "Durable repository unavailable",
        "detail": (
            "The configured durable repository is unavailable. Check database "
            "connectivity and configuration before running write-capable idea operations."
        ),
    }
    assert repository.__class__.__name__ == "UnavailableIdeaRepository"
    assert "secret" not in response.text
    assert "db.internal" not in response.text
    assert "could not connect" not in response.text


def test_high_cash_persist_api_replays_same_idempotency_payload() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    headers = persistence_headers("persist-high-cash-api-replay-001")
    first = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=headers,
    )

    replayed = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=headers,
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert (
        replayed.json()["persistence"]["candidateId"] == first.json()["persistence"]["candidateId"]
    )


def test_high_cash_persist_api_returns_existing_candidate_for_new_retry_key() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    first = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=persistence_headers("persist-high-cash-api-first-key"),
    )

    duplicate = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=persistence_headers("persist-high-cash-api-second-key"),
    )

    assert first.status_code == 200
    assert first.json()["persistence"]["decision"] == "accepted"
    assert duplicate.status_code == 200
    assert duplicate.json()["persistence"]["decision"] == "duplicate_candidate"
    assert (
        duplicate.json()["persistence"]["candidateId"] == first.json()["persistence"]["candidateId"]
    )
    assert len(get_idea_repository().snapshot().candidate_records) == 1


def test_high_cash_persist_api_versions_corrected_evidence_without_duplicate_candidate() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    first = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers=persistence_headers("persist-high-cash-api-correction-first"),
    )
    corrected_payload = high_cash_payload(scoped=True)
    projection_ref = corrected_payload["sourceEvidence"]["cashflowProjectionRef"]
    projection_ref["contentHash"] = "sha256:corrected-cashflow-projection"

    corrected = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=corrected_payload,
        headers=persistence_headers("persist-high-cash-api-correction-second"),
    )

    assert (first.status_code, corrected.status_code) == (200, 200)
    assert corrected.json()["persistence"]["decision"] == "evidence_refreshed"
    persistence = corrected.json()["persistence"]
    assert persistence["candidateId"] == first.json()["persistence"]["candidateId"]
    identity = persistence["identity"]
    assert (identity["materialVersion"], identity["evidenceVersion"]) == (1, 2)
    assert identity["changeReason"] == "evidence_correction"
    records = tuple(get_idea_repository().snapshot().candidate_records.values())
    assert (len(records), len(records[0].version_history)) == (1, 2)


def test_high_cash_persist_api_returns_conflict_for_changed_idempotency_payload() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    headers = persistence_headers("persist-high-cash-api-conflict-001")
    client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(cash_weight="0.18", scoped=True),
        headers=headers,
    )

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(cash_weight="0.20", scoped=True),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "type": "about:blank",
        "status": 409,
        "code": "idempotency_conflict",
        "title": "Idempotency conflict",
        "detail": "The idempotency key was already used with a different request payload.",
    }


def test_high_cash_persist_api_does_not_persist_blocked_evaluation() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(cash_weight=None, scoped=True),
        headers=persistence_headers("persist-high-cash-api-blocked-001"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluation"]["outcome"] == "blocked"
    assert payload["persistence"] is None
    assert payload["durableStorageBacked"] is False


def test_high_cash_persist_api_skips_not_eligible_evaluation() -> None:
    reset_idea_repository_for_tests()

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(cash_weight="0.05", scoped=True),
        headers=persistence_headers("persist-high-cash-api-not-eligible"),
    )

    assert response.status_code == 200
    assert response.json()["evaluation"]["outcome"] == "not_eligible"
    assert response.json()["evaluation"]["candidate"] is None
    assert response.json()["persistence"] is None
    assert response.json()["supportedFeaturePromoted"] is False
    assert len(get_idea_repository().snapshot().candidate_records) == 0


def test_high_cash_persist_api_requires_candidate_persistence_capability() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Roles": "advisor",
            "Idempotency-Key": "persist-high-cash-api-denied-001",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to persist idea candidates.",
    }


def test_high_cash_persist_api_rejects_blank_idempotency_key_safely() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(scoped=True),
        headers={
            "X-Caller-Subject": "signal-ingestion-worker",
            "X-Caller-Capabilities": "idea.candidate.persist",
            "Idempotency-Key": " ",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Idempotency-Key is required.",
    }
