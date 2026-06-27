from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_risk_sources import LotusRiskVolatilitySourceAdapter
from app.ports.risk_sources import (
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
    RiskVolatilityEvidenceRequest,
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
                "metrics": {
                    "VOLATILITY": {
                        "value": 14.25,
                        "details": {
                            "observation_count": 120,
                            "annualization_factor": 252,
                        },
                    }
                },
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "risk.v1",
            "generated_at": "2026-06-21T10:00:00Z",
            "request_fingerprint": "risk-metrics-fingerprint",
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


def _adapter(handler: httpx.MockTransport) -> LotusRiskVolatilitySourceAdapter:
    return LotusRiskVolatilitySourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://risk.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://risk.example", transport=handler),
        )
    )


def _request() -> RiskVolatilityEvidenceRequest:
    return RiskVolatilityEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        volatility_threshold=Decimal("14.0"),
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def test_lotus_risk_adapter_fetches_declared_volatility_source_product() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        assert request.headers["X-Correlation-Id"] == "corr-risk"
        assert request.headers["X-Trace-Id"] == "trace-risk"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_volatility_evidence(_request())

    assert evidence.source_reported_volatility == Decimal("14.25")
    assert evidence.risk_supportability_state == "ready"
    assert evidence.risk_ref is not None
    assert evidence.risk_ref.product_id == "lotus-risk:RiskMetricsReport:v1"
    assert evidence.risk_ref.route == "/analytics/risk/calculate"
    assert evidence.risk_ref.content_hash == "sha256:risk-metrics-fingerprint"
    assert evidence.risk_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.risk_diagnostic == "risk_volatility_source_ready"
    assert seen == [
        (
            "POST",
            "https://risk.example/analytics/risk/calculate",
            {
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "as_of_date": "2026-06-21",
                    "periods": [{"type": "YTD", "name": "YTD"}],
                    "metrics": ["VOLATILITY"],
                },
            },
        )
    ]


def test_lotus_risk_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(RiskSourceEntitlementDenied):
        adapter.fetch_volatility_evidence(_request())


def test_lotus_risk_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        adapter.fetch_volatility_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_risk_adapter_maps_missing_period_to_source_unavailable() -> None:
    payload = _payload(extra={"results": {}})

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_volatility_evidence(_request())

    assert exc_info.value.code == "risk_YTD_missing"


def test_lotus_risk_adapter_accepts_missing_volatility_as_source_gap() -> None:
    payload = _payload()
    volatility = payload["results"]["YTD"]["metrics"]["VOLATILITY"]
    assert isinstance(volatility, dict)
    volatility["value"] = None

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_volatility_evidence(_request())

    assert evidence.source_reported_volatility is None
    assert evidence.risk_diagnostic == "risk_volatility_value_missing"


def test_lotus_risk_adapter_maps_malformed_volatility_to_source_unavailable() -> None:
    payload = _payload()
    volatility = payload["results"]["YTD"]["metrics"]["VOLATILITY"]
    assert isinstance(volatility, dict)
    volatility["value"] = "not-decimal"

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_volatility_evidence(_request())

    assert exc_info.value.code == "risk_volatility_value_malformed"


def test_lotus_risk_adapter_maps_non_ready_supportability_to_unavailable_freshness() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {"state": "partial"}

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_volatility_evidence(_request())

    assert evidence.risk_supportability_state == "partial"
    assert evidence.risk_ref is not None
    assert evidence.risk_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_risk_volatility_evidence_request_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        RiskVolatilityEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            volatility_threshold=Decimal("14.0"),
        )

    with pytest.raises(ValueError, match="period_name is required"):
        RiskVolatilityEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name=" ",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            volatility_threshold=Decimal("14.0"),
        )
