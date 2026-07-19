from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest

from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import CoreBondMaturityEvidenceRequest, CoreSourceUnavailable


def _maturity_summary_payload(*, extra: dict[str, Any]) -> dict[str, Any]:
    maturity_hash = "sha256:" + "a" * 64
    payload: dict[str, Any] = {
        "product_name": "PortfolioMaturitySummary",
        "product_version": "v1",
        "as_of_date": "2026-06-21",
        "generated_at": "2026-06-21T10:00:00Z",
        "data_quality_status": "complete",
        "freshness": "current",
        "tenant_id": "tenant-a",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
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
        "request_fingerprint": "maturity_summary:0123456789abcdef",
        "snapshot_id": "holdings-snapshot-1",
        "content_hash": maturity_hash,
        "source_digest": maturity_hash,
        "source_batch_fingerprint": maturity_hash,
        "restatement_version": "restatement-v1",
        "reconciliation_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-06-21T09:59:00Z",
        "source_evidence_current": True,
        "policy_version": "holdings-policy-v1",
        "correlation_id": "corr-core",
        "source_lineage": {
            "source_owner": "lotus-core",
            "source_product": "PortfolioMaturitySummary",
            "upstream_product": "HoldingsAsOf",
            "upstream_content_hash": "sha256:" + "b" * 64,
        },
    }
    payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusCoreHighCashSourceAdapter:
    return LotusCoreHighCashSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://core.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://core.example", transport=handler),
        )
    )


def _request() -> CoreBondMaturityEvidenceRequest:
    return CoreBondMaturityEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        maturity_window_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


@pytest.mark.parametrize(
    ("extra", "expected_code"),
    [
        (
            {"latest_evidence_timestamp": "not-a-timestamp"},
            "core_latest_evidence_timestamp_malformed",
        ),
        (
            {"latest_evidence_timestamp": "2026-06-21T09:59:00"},
            "core_latest_evidence_timestamp_naive",
        ),
        ({"maturing_holding_count": -1}, "core_maturing_position_count_malformed"),
    ],
)
def test_adapter_rejects_malformed_maturity_trust_metadata(
    extra: dict[str, Any],
    expected_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_maturity_summary_payload(extra=extra))

    with pytest.raises(CoreSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(_request())

    assert exc_info.value.code == expected_code


def test_adapter_preserves_unsupported_maturity_diagnostic() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_maturity_summary_payload(extra={"supportability_status": "UNSUPPORTED"}),
        )

    evidence = _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(_request())

    assert evidence.maturity_diagnostic == "core_maturity_unsupported"


def test_adapter_forwards_tenant_and_trace_scope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Tenant-Id"] == "tenant-a"
        assert request.headers["X-Correlation-Id"] == "corr-core"
        assert request.headers["X-Trace-Id"] == "trace-core"
        return httpx.Response(200, json=_maturity_summary_payload(extra={}))

    evidence = _adapter(httpx.MockTransport(handler)).fetch_bond_maturity_evidence(_request())

    assert evidence.response_tenant_id == "tenant-a"
