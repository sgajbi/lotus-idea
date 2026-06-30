from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBondMaturityEvidenceRequest,
    CoreHighCashEvidenceRequest,
    CoreLowIncomeEvidenceRequest,
    CorePortfolioStateEvidenceRequest,
)


AS_OF_DATE = date(2026, 6, 21)


def _payload_without_freshness(
    product_name: str, *, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "product_name": product_name,
        "product_version": "v1",
        "as_of_date": "2026-06-21",
        "generated_at": "2026-06-21T10:00:00Z",
        "data_quality_status": "complete",
        "source_batch_fingerprint": f"{product_name.lower()}-fingerprint",
    }
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


def _high_cash_request() -> CoreHighCashEvidenceRequest:
    return CoreHighCashEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _benchmark_assignment_request() -> CoreBenchmarkAssignmentEvidenceRequest:
    return CoreBenchmarkAssignmentEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        reporting_currency="USD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _portfolio_state_request() -> CorePortfolioStateEvidenceRequest:
    return CorePortfolioStateEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _low_income_request() -> CoreLowIncomeEvidenceRequest:
    return CoreLowIncomeEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        horizon_days=45,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _bond_maturity_request() -> CoreBondMaturityEvidenceRequest:
    return CoreBondMaturityEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        maturity_window_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def test_lotus_core_adapter_maps_missing_high_cash_freshness_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json=_payload_without_freshness("PortfolioStateSnapshot"),
            )
        if "cash-balances" in str(request.url):
            return httpx.Response(
                200,
                json=_payload_without_freshness(
                    "HoldingsAsOf", extra={"sourceReportedCashWeight": "0.18"}
                ),
            )
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200, json=_payload_without_freshness("PortfolioCashMovementSummary")
            )
        return httpx.Response(200, json=_payload_without_freshness("PortfolioCashflowProjection"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_high_cash_evidence(_high_cash_request())

    source_refs = (
        evidence.portfolio_state_ref,
        evidence.holdings_ref,
        evidence.cash_movement_ref,
        evidence.cashflow_projection_ref,
    )
    non_null_source_refs = tuple(source_ref for source_ref in source_refs if source_ref is not None)
    assert len(non_null_source_refs) == 4
    assert all(
        source_ref.freshness is EvidenceFreshness.UNAVAILABLE for source_ref in non_null_source_refs
    )


def test_lotus_core_adapter_maps_missing_benchmark_assignment_freshness_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload_without_freshness(
                "BenchmarkAssignment",
                extra={
                    "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
                    "effective_from": "2026-01-01",
                    "assignment_status": "active",
                    "assignment_version": 3,
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_benchmark_assignment_evidence(
        _benchmark_assignment_request()
    )

    assert evidence.benchmark_assignment_ref is not None
    assert evidence.benchmark_assignment_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_core_adapter_maps_missing_portfolio_state_freshness_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload_without_freshness("PortfolioStateSnapshot"))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_portfolio_state_evidence(
        _portfolio_state_request()
    )

    assert evidence.portfolio_state_ref is not None
    assert evidence.portfolio_state_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_core_adapter_maps_missing_low_income_freshness_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload_without_freshness(
                    "PortfolioCashMovementSummary", extra={"cashflow_count": 1}
                ),
            )
        return httpx.Response(
            200,
            json=_payload_without_freshness(
                "PortfolioCashflowProjection", extra={"total_net_cashflow": "-11000"}
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(
        _low_income_request()
    )

    assert evidence.cash_movement_ref is not None
    assert evidence.cashflow_projection_ref is not None
    assert evidence.cash_movement_ref.freshness is EvidenceFreshness.UNAVAILABLE
    assert evidence.cashflow_projection_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_core_adapter_maps_missing_bond_maturity_freshness_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload_without_freshness(
                "HoldingsAsOf",
                extra={
                    "maturitySummary": {
                        "nextMaturityDate": "2026-07-10",
                        "maturingPositionCount": 1,
                        "source_batch_fingerprint": "bond-maturity-summary",
                    }
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(
        _bond_maturity_request()
    )

    assert evidence.holdings_ref is not None
    assert evidence.maturity_fact_ref is not None
    assert evidence.holdings_ref.freshness is EvidenceFreshness.UNAVAILABLE
    assert evidence.maturity_fact_ref.freshness is EvidenceFreshness.UNAVAILABLE
