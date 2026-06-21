from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreHighCashEvidenceRequest,
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


def _adapter(handler: httpx.MockTransport) -> LotusCoreHighCashSourceAdapter:
    return LotusCoreHighCashSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://core.example", transport=handler),
        )
    )


def _request() -> CoreHighCashEvidenceRequest:
    return CoreHighCashEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
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


def test_lotus_core_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(CoreSourceEntitlementDenied):
        adapter.fetch_high_cash_evidence(_request())


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


@pytest.mark.parametrize(
    ("freshness", "expected"),
    [
        ("EXPIRED_SOURCE", EvidenceFreshness.EXPIRED),
        ("SOURCE_UNAVAILABLE", EvidenceFreshness.UNAVAILABLE),
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


def test_lotus_core_adapter_maps_stale_freshness_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json=_payload("PortfolioStateSnapshot", extra={"freshness": "STALE_SOURCE"}),
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
    assert evidence.portfolio_state_ref.freshness is EvidenceFreshness.STALE


def test_core_high_cash_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        CoreHighCashEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_core_high_cash_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        CoreHighCashEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )
