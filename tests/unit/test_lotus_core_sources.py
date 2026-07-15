from __future__ import annotations

from datetime import UTC, date, datetime
from dataclasses import replace
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBondMaturityEvidenceRequest,
    CoreHighCashEvidenceRequest,
    CoreLowIncomeEvidenceRequest,
    CorePortfolioStateEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)


def _payload(product_name: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "product_name": product_name,
        "product_version": "v1",
        "as_of_date": "2026-06-21",
        "generated_at": "2026-06-21T10:00:00Z",
        "data_quality_status": "complete",
        "source_batch_fingerprint": f"{product_name.lower()}-fingerprint",
        "freshness": "current",
    }
    if extra:
        payload.update(extra)
    return payload


def _maturity_summary_payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _payload(
        "PortfolioMaturitySummary",
        extra={
            "source_product_name": "HoldingsAsOf",
            "source_product_version": "v1",
            "window_start_date": "2026-06-21",
            "window_end_date": "2026-07-21",
            "horizon_days": 30,
            "include_projected": False,
            "maturity_basis": "CONTRACTUAL_INSTRUMENT_MATURITY_DATE",
            "freshness_status": "CURRENT",
            "next_maturity_date": "2026-07-10",
            "maturing_holding_count": 1,
            "maturity_bearing_holding_count": 2,
            "missing_maturity_date_count": 0,
            "unsupported_maturity_feature_count": 0,
            "supportability_status": "SUPPORTED",
            "supportability_reasons": [],
            "request_fingerprint": "maturity_summary:abc123",
            "content_hash": "sha256:portfolio-maturity-summary",
            "source_batch_fingerprint": "sha256:portfolio-maturity-summary",
            "source_lineage": {
                "source_owner": "lotus-core",
                "source_product": "PortfolioMaturitySummary",
                "upstream_product": "HoldingsAsOf",
                "upstream_content_hash": "sha256:holdings-as-of",
            },
        },
    )
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusCoreHighCashSourceAdapter:
    return LotusCoreHighCashSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://core.example", transport=handler),
        )
    )


def _split_adapter(
    *,
    query_handler: httpx.MockTransport,
    query_control_plane_handler: httpx.MockTransport,
) -> LotusCoreHighCashSourceAdapter:
    return LotusCoreHighCashSourceAdapter(
        query_client=DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core-query.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://core-query.example", transport=query_handler),
        ),
        query_control_plane_client=DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core-control.example", timeout_seconds=0.5),
            client=httpx.Client(
                base_url="https://core-control.example",
                transport=query_control_plane_handler,
            ),
        ),
    )


def _request() -> CoreHighCashEvidenceRequest:
    return CoreHighCashEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _benchmark_assignment_request() -> CoreBenchmarkAssignmentEvidenceRequest:
    return CoreBenchmarkAssignmentEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        reporting_currency="USD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _portfolio_state_request() -> CorePortfolioStateEvidenceRequest:
    return CorePortfolioStateEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _low_income_request() -> CoreLowIncomeEvidenceRequest:
    return CoreLowIncomeEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        horizon_days=45,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _bond_maturity_request() -> CoreBondMaturityEvidenceRequest:
    return CoreBondMaturityEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        maturity_window_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def test_lotus_core_adapter_fetches_declared_high_cash_source_products() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        if request.method == "POST":
            assert json.loads(request.content)["consumer_system"] == "lotus-idea"
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioStateSnapshot",
                    extra={"request_fingerprint": "core-snapshot-fingerprint"},
                ),
            )
        url = str(request.url)
        if "cash-balances" in url:
            return httpx.Response(
                200,
                json=_payload("HoldingsAsOf", extra={"sourceReportedCashWeight": "0.18"}),
            )
        if "cash-movement-summary" in url:
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        if "cashflow-projection" in url:
            return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))
        raise AssertionError(f"unexpected URL {url}")

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert evidence.source_reported_cash_weight == Decimal("0.18")
    assert evidence.portfolio_state_ref is not None
    assert evidence.portfolio_state_ref.product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert evidence.holdings_ref is not None
    assert evidence.holdings_ref.product_id == "lotus-core:HoldingsAsOf:v1"
    assert evidence.cash_movement_ref is not None
    assert evidence.cash_movement_ref.product_id == "lotus-core:PortfolioCashMovementSummary:v1"
    assert evidence.cashflow_projection_ref is not None
    assert (
        evidence.cashflow_projection_ref.product_id == "lotus-core:PortfolioCashflowProjection:v1"
    )
    assert len(seen) == 4


def test_lotus_core_adapter_propagates_each_explicit_tenant() -> None:
    seen_tenants: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen_tenants.append(json.loads(request.content)["tenant_id"])
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioStateSnapshot",
                    extra={"request_fingerprint": "core-snapshot-fingerprint"},
                ),
            )
        url = str(request.url)
        if "cash-balances" in url:
            return httpx.Response(
                200,
                json=_payload("HoldingsAsOf", extra={"sourceReportedCashWeight": "0.18"}),
            )
        if "cash-movement-summary" in url:
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        if "cashflow-projection" in url:
            return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))
        raise AssertionError(f"unexpected URL {url}")

    adapter = _adapter(httpx.MockTransport(handler))
    adapter.fetch_high_cash_evidence(replace(_request(), tenant_id="tenant-a"))
    adapter.fetch_high_cash_evidence(replace(_request(), tenant_id="tenant-b"))

    assert seen_tenants == ["tenant-a", "tenant-b"]


def test_lotus_core_adapter_fetches_benchmark_assignment_source_product() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        payload = json.loads(request.content)
        assert payload == {"as_of_date": "2026-06-21", "reporting_currency": "USD"}
        return httpx.Response(
            200,
            json=_payload(
                "BenchmarkAssignment",
                extra={
                    "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
                    "effective_from": "2026-01-01",
                    "effective_to": None,
                    "assignment_status": "active",
                    "assignment_version": 3,
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_benchmark_assignment_evidence(
        _benchmark_assignment_request()
    )

    assert evidence.benchmark_assignment_ref is not None
    assert evidence.benchmark_assignment_ref.product_id == "lotus-core:BenchmarkAssignment:v1"
    assert evidence.benchmark_assignment_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.benchmark_identity_resolved is True
    assert evidence.assignment_effective_for_as_of_date is True
    assert evidence.assignment_status == "active"
    assert evidence.assignment_version_present is True
    assert evidence.assignment_diagnostic == "core_benchmark_assignment_ready"
    assert seen == [
        (
            "POST",
            "https://core.example/integration/portfolios/PB_SG_GLOBAL_BAL_001/benchmark-assignment",
        )
    ]


def test_lotus_core_adapter_fetches_portfolio_state_source_product() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        assert json.loads(request.content) == {
            "as_of_date": "2026-06-21",
            "snapshot_mode": "BASELINE",
            "consumer_system": "lotus-idea",
            "tenant_id": "tenant-a",
            "sections": ["portfolio_state", "portfolio_totals"],
        }
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioStateSnapshot",
                extra={
                    "tenant_id": "tenant-a",
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "snapshot_mode": "BASELINE",
                    "request_fingerprint": "core-snapshot-fingerprint",
                    "snapshot_id": "pss_test_snapshot",
                    "source_batch_fingerprint": "sha256:" + "a" * 64,
                    "content_hash": "sha256:" + "a" * 64,
                    "source_digest": "sha256:" + "a" * 64,
                    "restatement_version": "restatement-v1",
                    "reconciliation_status": "COMPLETE",
                    "latest_evidence_timestamp": "2026-06-21T09:59:00Z",
                    "source_evidence_current": True,
                    "policy_version": "tenant-policy-v1",
                    "correlation_id": "corr-core",
                    "governance": {
                        "tenant_id": "tenant-a",
                        "applied_sections": ["portfolio_state", "portfolio_totals"],
                        "dropped_sections": [],
                    },
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_portfolio_state_evidence(
        _portfolio_state_request()
    )

    assert evidence.portfolio_state_ref is not None
    assert evidence.portfolio_state_ref.product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert evidence.portfolio_state_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.source_evidence_available is True
    assert evidence.response_product_name == "PortfolioStateSnapshot"
    assert evidence.response_product_version == "v1"
    assert evidence.response_tenant_id == "tenant-a"
    assert evidence.response_portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert evidence.snapshot_mode == "BASELINE"
    assert evidence.snapshot_id == "pss_test_snapshot"
    assert evidence.source_batch_fingerprint == "sha256:" + "a" * 64
    assert evidence.response_content_hash == "sha256:" + "a" * 64
    assert evidence.response_source_digest == "sha256:" + "a" * 64
    assert evidence.restatement_version == "restatement-v1"
    assert evidence.reconciliation_status == "COMPLETE"
    assert evidence.latest_evidence_at_utc == datetime(2026, 6, 21, 9, 59, tzinfo=UTC)
    assert evidence.source_evidence_current is True
    assert evidence.policy_version == "tenant-policy-v1"
    assert evidence.source_correlation_id == "corr-core"
    assert evidence.applied_sections == ("portfolio_state", "portfolio_totals")
    assert evidence.dropped_sections == ()
    assert evidence.portfolio_state_diagnostic == "core_portfolio_state_ready"
    assert seen == [
        (
            "POST",
            "https://core.example/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        )
    ]


def test_lotus_core_adapter_fetches_low_income_cashflow_source_products() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        url = str(request.url)
        if "cash-movement-summary" in url:
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflow_count": 3}),
            )
        if "cashflow-projection" in url:
            assert "horizon_days=45" in url
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioCashflowProjection",
                    extra={
                        "points": [
                            {"projected_cumulative_cashflow": "-5000"},
                            {"projected_cumulative_cashflow": "-12500"},
                            {"projected_cumulative_cashflow": "-7500"},
                        ]
                    },
                ),
            )
        raise AssertionError(f"unexpected URL {url}")

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.source_reported_min_projected_cumulative_cashflow == Decimal("-12500")
    assert evidence.cash_movement_count == 3
    assert evidence.cash_movement_ref is not None
    assert evidence.cash_movement_ref.product_id == "lotus-core:PortfolioCashMovementSummary:v1"
    assert evidence.cashflow_projection_ref is not None
    assert (
        evidence.cashflow_projection_ref.product_id == "lotus-core:PortfolioCashflowProjection:v1"
    )
    assert evidence.cashflow_diagnostic == "core_cashflow_liquidity_evidence_ready"
    assert seen == [
        (
            "GET",
            "https://core.example/portfolios/PB_SG_GLOBAL_BAL_001/cash-movement-summary"
            "?start_date=2026-06-21&end_date=2026-06-21",
        ),
        (
            "GET",
            "https://core.example/portfolios/PB_SG_GLOBAL_BAL_001/cashflow-projection"
            "?as_of_date=2026-06-21&horizon_days=45&include_projected=true",
        ),
    ]


def test_lotus_core_adapter_fetches_bond_maturity_source_product() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        return httpx.Response(
            200,
            json=_maturity_summary_payload(),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
        _bond_maturity_request()
    )

    assert evidence.source_reported_next_maturity_date == date(2026, 7, 10)
    assert evidence.source_reported_maturing_position_count == 1
    assert evidence.holdings_ref is not None
    assert evidence.holdings_ref.product_id == "lotus-core:HoldingsAsOf:v1"
    assert evidence.holdings_ref.content_hash == "sha256:holdings-as-of"
    assert evidence.maturity_fact_ref is not None
    assert evidence.maturity_fact_ref.product_id == "lotus-core:PortfolioMaturitySummary:v1"
    assert evidence.maturity_fact_ref.content_hash == "sha256:portfolio-maturity-summary"
    assert evidence.maturity_diagnostic == "core_maturity_evidence_ready"
    assert seen == [
        "https://core.example/portfolios/PB_SG_GLOBAL_BAL_001/maturity-summary"
        "?as_of_date=2026-06-21&horizon_days=30&include_projected=false"
    ]


def test_lotus_core_adapter_blocks_missing_bond_maturity_upstream_lineage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_maturity_summary_payload(
                extra={
                    "source_product_name": "UnknownProduct",
                    "source_lineage": {},
                }
            ),
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
            _bond_maturity_request()
        )

    assert exc_info.value.code == "core_maturity_upstream_holdings_ref_missing"


def test_lotus_core_adapter_reports_bond_maturity_window_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_maturity_summary_payload(
                extra={
                    "next_maturity_date": "2026-08-15",
                    "maturing_holding_count": 0,
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
        _bond_maturity_request()
    )

    assert evidence.source_reported_next_maturity_date == date(2026, 8, 15)
    assert evidence.source_reported_maturing_position_count == 0
    assert evidence.maturity_diagnostic == "core_maturity_window_empty"


def test_lotus_core_adapter_maps_missing_maturing_count_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_maturity_summary_payload(
                extra={
                    "next_maturity_date": "2026-07-10",
                    "maturing_holding_count": None,
                },
            ),
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
            _bond_maturity_request()
        )

    assert exc_info.value.code == "core_maturing_position_count_missing"


def test_lotus_core_adapter_maps_malformed_bond_maturity_date_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_maturity_summary_payload(
                extra={
                    "next_maturity_date": "soon",
                    "maturing_holding_count": 1,
                },
            ),
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
            _bond_maturity_request()
        )

    assert exc_info.value.code == "core_maturity_date_malformed"


def test_lotus_core_adapter_uses_cashflow_projection_total_when_points_are_absent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflow_count": 1}),
            )
        return httpx.Response(
            200,
            json=_payload("PortfolioCashflowProjection", extra={"total_net_cashflow": "-11000"}),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.source_reported_min_projected_cumulative_cashflow == Decimal("-11000")


def test_lotus_core_adapter_reports_low_income_missing_projection_diagnostic() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflow_count": 1}),
            )
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.source_reported_min_projected_cumulative_cashflow is None
    assert evidence.cashflow_diagnostic == "core_cashflow_projection_missing"


def test_lotus_core_adapter_reports_low_income_missing_cash_movement_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(
            200,
            json=_payload("PortfolioCashflowProjection", extra={"totalNetCashflow": "-11000"}),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.cash_movement_count is None
    assert evidence.cashflow_diagnostic == "core_cash_movement_count_missing"


def test_lotus_core_adapter_handles_camel_case_low_income_projection_points() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflowCount": "2"}),
            )
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioCashflowProjection",
                extra={
                    "points": [
                        "ignored-point",
                        {},
                        {"projectedCumulativeCashflow": "-9500"},
                        {"projectedCumulativeCashflow": "-14500"},
                    ]
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.cash_movement_count == 2
    assert evidence.source_reported_min_projected_cumulative_cashflow == Decimal("-14500")


def test_lotus_core_adapter_marks_benchmark_assignment_not_effective_for_as_of_date() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload(
                "BenchmarkAssignment",
                extra={
                    "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
                    "effective_from": "2026-07-01",
                    "assignment_status": "active",
                    "assignment_version": 3,
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_benchmark_assignment_evidence(
        _benchmark_assignment_request()
    )

    assert evidence.benchmark_identity_resolved is True
    assert evidence.assignment_effective_for_as_of_date is False
    assert (
        evidence.assignment_diagnostic == "core_benchmark_assignment_not_effective_for_as_of_date"
    )


def test_lotus_core_adapter_marks_benchmark_assignment_missing_effective_date_and_identity() -> (
    None
):
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {"as_of_date": "2026-06-21"}
        return httpx.Response(
            200,
            json=_payload(
                "BenchmarkAssignment",
                extra={"assignment_status": "active", "assignment_version": 3},
            ),
        )

    request = CoreBenchmarkAssignmentEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    )
    evidence = _adapter(httpx.MockTransport(handler)).fetch_benchmark_assignment_evidence(request)

    assert evidence.benchmark_identity_resolved is False
    assert evidence.assignment_effective_for_as_of_date is False
    assert evidence.assignment_diagnostic == "core_benchmark_assignment_benchmark_identity_missing"


@pytest.mark.parametrize(
    ("extra", "expected_diagnostic"),
    [
        (
            {"benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40", "effective_from": "2026-01-01"},
            "core_benchmark_assignment_status_missing",
        ),
        (
            {
                "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
                "effective_from": "2026-01-01",
                "assignment_status": "inactive",
                "assignment_version": 3,
            },
            "core_benchmark_assignment_inactive",
        ),
        (
            {
                "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
                "effective_from": "2026-01-01",
                "assignment_status": "active",
            },
            "core_benchmark_assignment_version_missing",
        ),
    ],
)
def test_lotus_core_adapter_reports_benchmark_assignment_diagnostics(
    extra: dict[str, Any],
    expected_diagnostic: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload("BenchmarkAssignment", extra=extra),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_benchmark_assignment_evidence(
        _benchmark_assignment_request()
    )

    assert evidence.assignment_diagnostic == expected_diagnostic


def test_lotus_core_adapter_splits_query_and_control_plane_clients() -> None:
    seen_query: list[str] = []
    seen_control_plane: list[str] = []

    def query_handler(request: httpx.Request) -> httpx.Response:
        seen_query.append(str(request.url))
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("HoldingsAsOf", extra={"sourceReportedCashWeight": "0.18"}),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        if "cashflow-projection" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))
        raise AssertionError(f"unexpected query URL {request.url}")

    def control_plane_handler(request: httpx.Request) -> httpx.Response:
        seen_control_plane.append(str(request.url))
        assert request.method == "POST"
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioStateSnapshot",
                extra={"request_fingerprint": "core-snapshot-fingerprint"},
            ),
        )

    evidence = _split_adapter(
        query_handler=httpx.MockTransport(query_handler),
        query_control_plane_handler=httpx.MockTransport(control_plane_handler),
    ).fetch_high_cash_evidence(_request())

    assert evidence.source_reported_cash_weight == Decimal("0.18")
    assert len(seen_control_plane) == 1
    assert "core-snapshot" in seen_control_plane[0]
    assert len(seen_query) == 3
    assert all("core-query.example" in url for url in seen_query)


def test_lotus_core_adapter_consumes_core_totals_source_reported_cash_weight() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_payload("PortfolioStateSnapshot"))
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "HoldingsAsOf",
                    extra={
                        "totals": {
                            "source_reported_cash_weight": "0.1835",
                            "source_reported_cash_weight_denominator_portfolio_currency": "2000000",
                            "source_reported_cash_weight_supportability": "SUPPORTED",
                        }
                    },
                ),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert evidence.source_reported_cash_weight == Decimal("0.1835")
    assert evidence.cash_weight_diagnostic == "core_cash_weight_supported"


@pytest.mark.parametrize(
    "supportability",
    [
        "BLOCKED_MISSING_DENOMINATOR",
        "BLOCKED_ZERO_DENOMINATOR",
        "BLOCKED_STALE_DENOMINATOR",
    ],
)
def test_lotus_core_adapter_blocks_cash_weight_when_core_supportability_is_blocked(
    supportability: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_payload("PortfolioStateSnapshot"))
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "HoldingsAsOf",
                    extra={
                        "totals": {
                            "source_reported_cash_weight": "0.25",
                            "source_reported_cash_weight_denominator_portfolio_currency": None,
                            "source_reported_cash_weight_supportability": supportability,
                        }
                    },
                ),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert evidence.source_reported_cash_weight is None
    assert evidence.cash_weight_diagnostic == f"core_cash_weight_{supportability.lower()}"


def test_lotus_core_adapter_keeps_cash_weight_missing_when_source_omits_it() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_payload("PortfolioStateSnapshot"))
        if "cash-balances" in str(request.url):
            return httpx.Response(200, json=_payload("HoldingsAsOf"))
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert evidence.source_reported_cash_weight is None
    assert evidence.cash_weight_diagnostic == "core_cash_weight_missing"


def test_lotus_core_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_high_cash_evidence(_request())


def test_lotus_core_adapter_maps_benchmark_assignment_forbidden_response_to_entitlement_denied() -> (
    None
):
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_benchmark_assignment_evidence(_benchmark_assignment_request())


def test_lotus_core_adapter_maps_portfolio_state_forbidden_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_portfolio_state_evidence(_portfolio_state_request())


def test_lotus_core_adapter_maps_low_income_forbidden_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_low_income_evidence(_low_income_request())


def test_lotus_core_adapter_maps_benchmark_assignment_source_error_to_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(CoreSourceUnavailable):
        adapter.fetch_benchmark_assignment_evidence(_benchmark_assignment_request())


def test_lotus_core_adapter_maps_portfolio_state_source_error_to_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(CoreSourceUnavailable):
        adapter.fetch_portfolio_state_evidence(_portfolio_state_request())


def test_lotus_core_adapter_maps_high_cash_source_error_to_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(CoreSourceUnavailable):
        adapter.fetch_high_cash_evidence(_request())


def test_lotus_core_adapter_maps_low_income_source_error_to_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        adapter.fetch_low_income_evidence(_low_income_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_core_adapter_maps_bond_maturity_forbidden_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_bond_maturity_evidence(_bond_maturity_request())


def test_lotus_core_adapter_maps_missing_runtime_metadata_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"product_name": "PortfolioStateSnapshot"})

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_generated_at_missing"


def test_lotus_core_adapter_maps_missing_as_of_date_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "product_name": "PortfolioStateSnapshot",
                "generated_at": "2026-06-21T10:00:00Z",
                "source_batch_fingerprint": "snapshot-fingerprint",
            },
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_as_of_date_missing"


def test_lotus_core_adapter_maps_missing_content_hash_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "product_name": "PortfolioStateSnapshot",
                "generated_at": "2026-06-21T10:00:00Z",
                "as_of_date": "2026-06-21",
            },
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_content_hash_missing"


def test_lotus_core_adapter_maps_naive_generated_at_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload("PortfolioStateSnapshot", extra={"generated_at": "2026-06-21T10:00:00"}),
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_generated_at_naive"


def test_lotus_core_adapter_maps_malformed_cash_weight_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_payload("PortfolioStateSnapshot"))
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("HoldingsAsOf", extra={"sourceReportedCashWeight": "not-decimal"}),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_cash_weight_malformed"


def test_lotus_core_adapter_maps_malformed_low_income_projection_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflow_count": 1}),
            )
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioCashflowProjection",
                extra={"points": [{"projected_cumulative_cashflow": "not-decimal"}]},
            ),
        )

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(_low_income_request())

    assert exc_info.value.code == "core_cashflow_projection_malformed"


def test_lotus_core_adapter_maps_malformed_low_income_count_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("PortfolioCashMovementSummary", extra={"cashflow_count": "many"}),
            )
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(_low_income_request())

    assert exc_info.value.code == "core_cashflow_count_malformed"


def test_lotus_core_adapter_maps_malformed_nested_cash_weight_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_payload("PortfolioStateSnapshot"))
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "HoldingsAsOf",
                    extra={
                        "totals": {
                            "source_reported_cash_weight": "not-decimal",
                            "source_reported_cash_weight_supportability": "SUPPORTED",
                        }
                    },
                ),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert exc_info.value.code == "core_cash_weight_malformed"


@pytest.mark.parametrize(
    ("freshness", "expected"),
    [
        ("CURRENT_SOURCE", EvidenceFreshness.CURRENT),
        ("current", EvidenceFreshness.CURRENT),
        ("STALE_SOURCE", EvidenceFreshness.STALE),
        ("EXPIRED_SOURCE", EvidenceFreshness.EXPIRED),
        ("SOURCE_UNAVAILABLE", EvidenceFreshness.UNAVAILABLE),
        ("unexpected", EvidenceFreshness.UNAVAILABLE),
    ],
)
def test_lotus_core_adapter_maps_additional_freshness_metadata(
    freshness: str, expected: EvidenceFreshness
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json=_payload("PortfolioStateSnapshot", extra={"freshness": freshness}),
            )
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload("HoldingsAsOf", extra={"sourceReportedCashWeight": "0.18"}),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(200, json=_payload("PortfolioCashMovementSummary"))
        return httpx.Response(200, json=_payload("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_request())

    assert evidence.portfolio_state_ref is not None
    assert evidence.portfolio_state_ref.freshness is expected


def test_core_high_cash_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        CoreHighCashEvidenceRequest(
            portfolio_id=" ",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_core_high_cash_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        CoreHighCashEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )


def test_core_benchmark_assignment_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        CoreBenchmarkAssignmentEvidenceRequest(
            portfolio_id=" ",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_core_benchmark_assignment_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        CoreBenchmarkAssignmentEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )


def test_core_portfolio_state_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        CorePortfolioStateEvidenceRequest(
            portfolio_id=" ",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_core_portfolio_state_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        CorePortfolioStateEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )


def test_core_low_income_evidence_request_requires_valid_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_days must be between 1 and 366"):
        CoreLowIncomeEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            horizon_days=0,
        )


def test_core_low_income_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        CoreLowIncomeEvidenceRequest(
            portfolio_id=" ",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_core_low_income_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        CoreLowIncomeEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            tenant_id="tenant-a",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )
