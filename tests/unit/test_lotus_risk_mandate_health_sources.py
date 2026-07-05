from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_risk_sources import LotusRiskMandateHealthSourceAdapter
from app.ports.risk_sources import (
    RiskMandateHealthContextRequest,
    RiskReturnObservation,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def _adapter(handler: httpx.MockTransport) -> LotusRiskMandateHealthSourceAdapter:
    return LotusRiskMandateHealthSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://risk.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://risk.example", transport=handler),
        )
    )


def test_lotus_risk_adapter_fetches_mandate_health_source_product_ref() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        assert request.headers["X-Correlation-Id"] == "corr-risk"
        assert request.headers["X-Trace-Id"] == "trace-risk"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_mandate_health_context(_request())

    assert evidence.health_state == "ready"
    assert evidence.threshold_breached is False
    assert evidence.risk_diagnostic == "MANDATE_RISK_HEALTH_TRACKING_ERROR_SOURCE_READY"
    assert evidence.mandate_risk_health_ref.product_id == "lotus-risk:MandateRiskHealthContext:v1"
    assert evidence.mandate_risk_health_ref.route == "/analytics/risk/mandate-health-context"
    assert evidence.mandate_risk_health_ref.content_hash == "sha256:risk-health-request"
    assert evidence.mandate_risk_health_ref.data_quality_status == "ready"
    assert evidence.mandate_risk_health_ref.freshness is EvidenceFreshness.UNAVAILABLE
    assert seen == [
        (
            "POST",
            "https://risk.example/analytics/risk/mandate-health-context",
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "scope": {
                    "as_of_date": "2026-06-21",
                    "net_or_gross": "NET",
                    "reporting_currency": "USD",
                },
                "period": {"type": "YTD", "name": "YTD"},
                "portfolio_open_date": "2024-01-01",
                "returns": [{"date": "2026-06-20", "value": "0.12"}],
                "benchmark_returns": [{"date": "2026-06-20", "value": "0.09"}],
                "tracking_error_attention_threshold": "0.05",
            },
        )
    ]


def test_lotus_risk_adapter_rejects_mandate_health_product_mismatch() -> None:
    payload = _payload(extra={"product_name": "RiskMetricsReport"})

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_mandate_health_context(_request())

    assert exc_info.value.code == "risk_mandate_health_product_mismatch"


def test_lotus_risk_adapter_maps_mandate_health_forbidden_response() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(RiskSourceEntitlementDenied):
        adapter.fetch_mandate_health_context(_request())


def test_risk_mandate_health_request_validates_governed_request_shape() -> None:
    with pytest.raises(ValueError, match="returns are required"):
        RiskMandateHealthContextRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            portfolio_open_date=date(2024, 1, 1),
            returns=(),
            benchmark_returns=_benchmark_observations(),
            evaluated_at_utc=EVALUATED_AT,
        )

    with pytest.raises(ValueError, match="benchmark_returns are required"):
        RiskMandateHealthContextRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            portfolio_open_date=date(2024, 1, 1),
            returns=_observations(),
            benchmark_returns=(),
            evaluated_at_utc=EVALUATED_AT,
        )

    with pytest.raises(ValueError, match="tracking_error_attention_threshold"):
        RiskMandateHealthContextRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            portfolio_open_date=date(2024, 1, 1),
            returns=_observations(),
            benchmark_returns=_benchmark_observations(),
            evaluated_at_utc=EVALUATED_AT,
            tracking_error_attention_threshold=Decimal("-0.01"),
        )

    with pytest.raises(ValueError, match="net_or_gross"):
        RiskMandateHealthContextRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            portfolio_open_date=date(2024, 1, 1),
            returns=_observations(),
            benchmark_returns=_benchmark_observations(),
            evaluated_at_utc=EVALUATED_AT,
            net_or_gross="BOTH",
        )


def _request() -> RiskMandateHealthContextRequest:
    return RiskMandateHealthContextRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        portfolio_open_date=date(2024, 1, 1),
        returns=_observations(),
        benchmark_returns=_benchmark_observations(),
        evaluated_at_utc=EVALUATED_AT,
        tracking_error_attention_threshold=Decimal("0.05"),
        reporting_currency="USD",
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def _observations() -> tuple[RiskReturnObservation, ...]:
    return (
        RiskReturnObservation(
            observation_date=date(2026, 6, 20),
            return_value=Decimal("0.12"),
        ),
    )


def _benchmark_observations() -> tuple[RiskReturnObservation, ...]:
    return (
        RiskReturnObservation(
            observation_date=date(2026, 6, 20),
            return_value=Decimal("0.09"),
        ),
    )


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "product_name": "MandateRiskHealthContext",
        "product_version": "v1",
        "lineage_version": "mandate-risk-health-context.v1",
        "source_services": ["lotus-risk"],
        "upstream_request_fingerprints": {},
        "benchmark_context": {"requested": True, "reason": "APPLIED"},
        "correlation_id": "corr-risk",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-06-21",
        "period_name": "YTD",
        "health_state": "ready",
        "threshold_breached": False,
        "tracking_error_attention_threshold": "0.05",
        "source_metric": {
            "metric_name": "TRACKING_ERROR",
            "annualized_tracking_error": "0.0425",
            "aligned_observation_count": 64,
        },
        "methodology_posture": {
            "source_product_name": "MandateRiskHealthContext",
            "source_product_version": "v1",
            "source_service": "lotus-risk",
            "source_metrics_product": "RiskMetricsReport:v1",
            "methodology_version": "risk.v1",
            "source_route": "/analytics/risk/calculate",
        },
        "request_fingerprint": "sha256:risk-health-request",
        "source_request_fingerprint": "sha256:risk-metrics-request",
        "reason_codes": [
            "MANDATE_RISK_HEALTH_TRACKING_ERROR_SOURCE_READY",
            "RISK_METHODOLOGY_SOURCE_OWNED",
        ],
    }
    if extra:
        payload.update(extra)
    return payload
