from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_risk_sources import LotusRiskDrawdownSourceAdapter
from app.ports.risk_sources import (
    RiskDrawdownEvidenceRequest,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scope": {
            "as_of_date": "2026-06-21",
            "reporting_currency": "USD",
            "net_or_gross": "NET",
        },
        "results": {
            "YTD": {
                "start_date": "2026-01-01",
                "end_date": "2026-06-21",
                "portfolio_observation_count": 120,
                "benchmark_observation_count": 0,
                "summary": {
                    "max_drawdown": -0.1245,
                    "max_drawdown_peak_date": "2026-02-01",
                    "max_drawdown_trough_date": "2026-03-11",
                    "is_recovered": False,
                    "time_under_water_days": 34,
                },
                "episodes": [],
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "drawdown.v1",
            "generated_at": "2026-06-21T10:00:00Z",
            "request_fingerprint": "drawdown-fingerprint",
            "calculation_supportability": {
                "state": "ready",
                "reason": "calculation_complete",
                "freshness_bucket": "current",
            },
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusRiskDrawdownSourceAdapter:
    return LotusRiskDrawdownSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://risk.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://risk.example", transport=handler),
        )
    )


def _request() -> RiskDrawdownEvidenceRequest:
    return RiskDrawdownEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        drawdown_threshold=Decimal("-0.08"),
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def test_lotus_risk_adapter_fetches_declared_drawdown_source_product() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        assert request.headers["X-Correlation-Id"] == "corr-risk"
        assert request.headers["X-Trace-Id"] == "trace-risk"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_drawdown_evidence(_request())

    assert evidence.source_reported_max_drawdown == Decimal("-0.1245")
    assert evidence.risk_supportability_state == "ready"
    assert evidence.risk_ref is not None
    assert evidence.risk_ref.product_id == "lotus-risk:DrawdownAnalyticsReport:v1"
    assert evidence.risk_ref.route == "/analytics/risk/drawdown"
    assert evidence.risk_ref.content_hash == "sha256:drawdown-fingerprint"
    assert evidence.risk_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.risk_diagnostic == "risk_drawdown_source_ready"
    assert seen == [
        (
            "POST",
            "https://risk.example/analytics/risk/drawdown",
            {
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "as_of_date": "2026-06-21",
                    "periods": [{"type": "YTD", "name": "YTD"}],
                    "benchmark_policy": {
                        "include_benchmark": False,
                        "missing_benchmark_policy": "IGNORE",
                    },
                },
                "analysis_options": {
                    "include_underwater_series": False,
                    "include_episode_list": True,
                    "top_n_episodes": 5,
                    "cdar_alpha": 0.95,
                    "minimum_episode_depth_bps": 0.0,
                    "duration_unit": "BUSINESS_DAYS",
                },
            },
        )
    ]


def test_lotus_risk_drawdown_adapter_maps_forbidden_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(RiskSourceEntitlementDenied):
        adapter.fetch_drawdown_evidence(_request())


def test_lotus_risk_drawdown_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        adapter.fetch_drawdown_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_risk_drawdown_adapter_maps_missing_period_to_source_unavailable() -> None:
    payload = _payload(extra={"results": {}})

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_drawdown_evidence(_request())

    assert exc_info.value.code == "risk_YTD_missing"


def test_lotus_risk_drawdown_adapter_accepts_missing_value_as_source_gap() -> None:
    payload = _payload()
    summary = payload["results"]["YTD"]["summary"]
    assert isinstance(summary, dict)
    summary["max_drawdown"] = None

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_drawdown_evidence(_request())

    assert evidence.source_reported_max_drawdown is None
    assert evidence.risk_diagnostic == "risk_drawdown_value_missing"


def test_lotus_risk_drawdown_adapter_maps_malformed_value_to_source_unavailable() -> None:
    payload = _payload()
    summary = payload["results"]["YTD"]["summary"]
    assert isinstance(summary, dict)
    summary["max_drawdown"] = "not-decimal"

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_drawdown_evidence(_request())

    assert exc_info.value.code == "risk_drawdown_value_malformed"


def test_lotus_risk_drawdown_adapter_maps_non_ready_supportability_to_unavailable_freshness() -> (
    None
):
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {"state": "partial"}

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_drawdown_evidence(_request())

    assert evidence.risk_supportability_state == "partial"
    assert evidence.risk_ref is not None
    assert evidence.risk_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_risk_drawdown_adapter_requires_declared_freshness_for_ready_source() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    supportability = metadata["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.pop("freshness_bucket")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_drawdown_evidence(_request())

    assert evidence.risk_supportability_state == "ready"
    assert evidence.risk_ref is not None
    assert evidence.risk_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_risk_drawdown_evidence_request_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        RiskDrawdownEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            drawdown_threshold=Decimal("-0.08"),
        )

    with pytest.raises(ValueError, match="period_name is required"):
        RiskDrawdownEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name=" ",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            drawdown_threshold=Decimal("-0.08"),
        )

    with pytest.raises(ValueError, match="drawdown_threshold"):
        RiskDrawdownEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            drawdown_threshold=Decimal("0.01"),
        )
