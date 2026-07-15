from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import CoreLowIncomeEvidenceRequest


def test_core_adapter_fetches_both_cashflow_products_with_request_context() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioCashMovementSummary",
                    content_hash="sha256:" + "c" * 64,
                    extra={"cashflow_count": 3},
                ),
            )
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioCashflowProjection",
                content_hash="sha256:" + "d" * 64,
                extra={
                    "points": [
                        {"projected_cumulative_cashflow": "-5000"},
                        {"projected_cumulative_cashflow": "-12500"},
                        {"projected_cumulative_cashflow": "-7500"},
                    ]
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(_request())

    assert evidence.source_reported_min_projected_cumulative_cashflow == Decimal("-12500")
    assert evidence.cash_movement_count == 3
    assert evidence.cash_movement_ref is not None
    assert evidence.cash_movement_ref.product_id == "lotus-core:PortfolioCashMovementSummary:v1"
    assert evidence.cashflow_projection_ref is not None
    assert evidence.cashflow_projection_ref.product_id == (
        "lotus-core:PortfolioCashflowProjection:v1"
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


def test_core_adapter_preserves_low_income_source_product_receipts() -> None:
    movement_hash = "sha256:" + "c" * 64
    projection_hash = "sha256:" + "d" * 64

    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioCashMovementSummary",
                    content_hash=movement_hash,
                    extra={
                        "start_date": "2026-06-21",
                        "end_date": "2026-06-21",
                        "buckets": [
                            {
                                "classification": "CASHFLOW_OUT",
                                "timing": "SETTLED",
                                "currency": "USD",
                                "is_position_flow": False,
                                "is_portfolio_flow": True,
                                "cashflow_count": 1,
                                "total_amount": "-12500",
                                "movement_direction": "OUTFLOW",
                            }
                        ],
                        "cashflow_count": 1,
                    },
                ),
            )
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioCashflowProjection",
                content_hash=projection_hash,
                extra={
                    "range_start_date": "2026-06-21",
                    "range_end_date": "2026-08-05",
                    "include_projected": True,
                    "portfolio_currency": "USD",
                    "points": [
                        {
                            "projection_date": "2026-06-21",
                            "booked_net_cashflow": "0",
                            "projected_settlement_cashflow": "-12500",
                            "net_cashflow": "-12500",
                            "projected_cumulative_cashflow": "-12500",
                        }
                    ],
                    "total_net_cashflow": "-12500",
                    "booked_total_net_cashflow": "0",
                    "projected_settlement_total_cashflow": "-12500",
                    "projection_days": 45,
                },
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(_request())

    movement = evidence.cash_movement_product
    projection = evidence.cashflow_projection_product
    assert movement is not None
    assert movement.runtime.content_hash == movement_hash
    assert movement.runtime.source_lineage == (("source_owner", "lotus-core"),)
    assert movement.buckets[0].total_amount == Decimal("-12500")
    assert projection is not None
    assert projection.runtime.content_hash == projection_hash
    assert projection.range_end_date == date(2026, 8, 5)
    assert projection.points[0].booked_net_cashflow == Decimal("0")
    assert projection.points[0].projected_cumulative_cashflow == Decimal("-12500")


@pytest.mark.parametrize(
    ("projection_payload", "expected"),
    [
        ({"points": [{"projected_cumulative_cashflow": 0}]}, Decimal("0")),
        ({"total_net_cashflow": 0}, Decimal("0")),
    ],
)
def test_core_adapter_preserves_zero_projection_evidence(
    projection_payload: dict[str, Any],
    expected: Decimal,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "cash-movement-summary" in str(request.url):
            return httpx.Response(
                200,
                json=_payload(
                    "PortfolioCashMovementSummary",
                    content_hash="sha256:" + "c" * 64,
                    extra={"cashflow_count": 0},
                ),
            )
        return httpx.Response(
            200,
            json=_payload(
                "PortfolioCashflowProjection",
                content_hash="sha256:" + "d" * 64,
                extra=projection_payload,
            ),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_low_income_evidence(_request())

    assert evidence.source_reported_min_projected_cumulative_cashflow == expected
    assert evidence.cash_movement_count == 0
    assert evidence.cashflow_diagnostic == "core_cashflow_liquidity_evidence_ready"


def _payload(
    product_name: str,
    *,
    content_hash: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    return {
        "product_name": product_name,
        "product_version": "v1",
        "tenant_id": "tenant-a",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-06-21",
        "generated_at": "2026-06-21T10:00:00Z",
        "restatement_version": "restatement-v1",
        "reconciliation_status": "COMPLETE",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-06-21T09:59:00Z",
        "source_batch_fingerprint": content_hash,
        "snapshot_id": "cashflow-snapshot-1",
        "content_hash": content_hash,
        "source_digest": content_hash,
        "source_refs": ["lotus-core://source/cashflow/1"],
        "source_lineage": {"source_owner": "lotus-core"},
        "degradation": {"status": "NONE", "reason_codes": [], "details": []},
        "source_evidence_current": True,
        "freshness_status": "CURRENT",
        "policy_version": "cashflow-policy-v1",
        "correlation_id": "corr-core",
        **extra,
    }


def _request() -> CoreLowIncomeEvidenceRequest:
    return CoreLowIncomeEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        horizon_days=45,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _adapter(transport: httpx.MockTransport) -> LotusCoreHighCashSourceAdapter:
    return LotusCoreHighCashSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://core.example", transport=transport),
        )
    )
