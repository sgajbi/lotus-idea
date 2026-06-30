from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidenceRequest,
)


AS_OF_DATE = date(2026, 6, 21)


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "calculation_id": "2f4f3e0e-6e0e-4e0e-8e0e-2f4f3e0e6e0e",
        "source_service": "lotus-performance",
        "contract_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-06-21",
        "frequency": "DAILY",
        "metric_basis": "NET",
        "resolved_window": {
            "start_date": "2026-01-01",
            "end_date": "2026-06-21",
            "resolved_period_label": "YTD",
        },
        "benchmark_context": {
            "benchmark_id": "BMK_PRIVATE_BANKING_BALANCED",
            "return_source": "calculated",
        },
        "series": {
            "portfolio_returns": [{"date": "2026-06-21", "return_value": "0.001"}],
            "cumulative_active_returns": [
                {"date": "2026-06-20", "return_value": "-0.004"},
                {"date": "2026-06-21", "return_value": "-0.0125"},
            ],
        },
        "provenance": {
            "input_mode": "stateful",
            "input_fingerprint": "returns-series-input",
            "calculation_hash": "returns-series-calculation",
        },
        "diagnostics": {
            "freshness": "current",
            "coverage": {
                "requested_points": 120,
                "returned_points": 120,
                "missing_points": 0,
                "coverage_ratio": "1.0",
            },
            "gaps": [],
            "warnings": [],
        },
        "metadata": {
            "generated_at": "2026-06-21T10:00:00Z",
            "correlation_id": "corr-performance",
            "trace_id": "trace-performance",
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusPerformanceUnderperformanceSourceAdapter:
    return LotusPerformanceUnderperformanceSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://performance.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://performance.example", transport=handler),
        )
    )


def _request() -> PerformanceUnderperformanceEvidenceRequest:
    return PerformanceUnderperformanceEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        active_return_threshold=Decimal("-0.005"),
        reporting_currency="USD",
        correlation_id="corr-performance",
        trace_id="trace-performance",
    )


def test_lotus_performance_adapter_fetches_declared_returns_series_source_product() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        assert request.headers["X-Correlation-Id"] == "corr-performance"
        assert request.headers["X-Trace-Id"] == "trace-performance"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_underperformance_evidence(_request())

    assert evidence.source_reported_active_return == Decimal("-0.0125")
    assert evidence.benchmark_context_available is True
    assert evidence.performance_ref is not None
    assert evidence.performance_ref.product_id == "lotus-performance:ReturnsSeriesBundle:v1"
    assert evidence.performance_ref.route == "/integration/returns/series"
    assert evidence.performance_ref.content_hash == "sha256:returns-series-calculation"
    assert evidence.performance_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.performance_diagnostic == "performance_benchmark_context_ready"
    assert seen == [
        (
            "POST",
            "https://performance.example/integration/returns/series",
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of_date": "2026-06-21",
                "window": {"mode": "RELATIVE", "period": "YTD"},
                "frequency": "DAILY",
                "metric_basis": "NET",
                "series_selection": {
                    "include_portfolio": True,
                    "include_benchmark": True,
                    "include_risk_free": False,
                },
                "data_policy": {
                    "missing_data_policy": "ALLOW_PARTIAL",
                    "fill_method": "NONE",
                    "calendar_policy": "BUSINESS",
                },
                "input_mode": "stateful",
                "stateful_input": {},
                "reporting_currency": "USD",
            },
        )
    ]


def test_lotus_performance_adapter_blocks_when_benchmark_context_missing() -> None:
    payload = _payload()
    payload.pop("benchmark_context")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.benchmark_context_available is False
    assert evidence.performance_diagnostic == "performance_benchmark_context_missing"


def test_lotus_performance_adapter_fetches_benchmark_readiness_without_active_return() -> None:
    payload = _payload()
    payload.pop("benchmark_context")
    series = payload["series"]
    assert isinstance(series, dict)
    series.pop("cumulative_active_returns")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_benchmark_readiness_evidence(_benchmark_readiness_request())

    assert evidence.benchmark_context_available is False
    assert evidence.performance_ref is not None
    assert evidence.performance_ref.product_id == "lotus-performance:ReturnsSeriesBundle:v1"
    assert evidence.performance_ref.route == "/integration/returns/series"
    assert evidence.performance_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.performance_diagnostic == "performance_benchmark_context_missing"


def test_lotus_performance_adapter_does_not_derive_active_return_locally() -> None:
    payload = _payload()
    series = payload["series"]
    assert isinstance(series, dict)
    series.pop("cumulative_active_returns")
    series["cumulative_portfolio_returns"] = [{"date": "2026-06-21", "return_value": "0.024"}]
    series["cumulative_benchmark_returns"] = [{"date": "2026-06-21", "return_value": "0.0365"}]

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.source_reported_active_return is None
    assert evidence.benchmark_context_available is True


def test_lotus_performance_adapter_maps_forbidden_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(PerformanceSourceEntitlementDenied):
        adapter.fetch_underperformance_evidence(_request())


def test_lotus_performance_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        adapter.fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_performance_adapter_maps_benchmark_readiness_forbidden_response() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(PerformanceSourceEntitlementDenied):
        adapter.fetch_benchmark_readiness_evidence(_benchmark_readiness_request())


def test_lotus_performance_adapter_maps_benchmark_readiness_server_error() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        adapter.fetch_benchmark_readiness_evidence(_benchmark_readiness_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_performance_adapter_rejects_source_service_mismatch() -> None:
    payload = _payload(extra={"source_service": "lotus-risk"})

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_source_service_mismatch"


def test_lotus_performance_adapter_maps_pending_async_response_to_source_unavailable() -> None:
    payload = {
        "source_service": "lotus-performance",
        "contract_version": "v1",
        "execution_mode": "async",
        "status": "pending",
        "result_path": "/integration/returns/series/results/example",
    }

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_returns_series_pending"


def test_lotus_performance_adapter_rejects_benchmark_readiness_source_service_mismatch() -> None:
    payload = _payload(extra={"source_service": "lotus-risk"})

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_benchmark_readiness_evidence(_benchmark_readiness_request())

    assert exc_info.value.code == "performance_source_service_mismatch"


def test_lotus_performance_adapter_maps_benchmark_readiness_pending_async_response() -> None:
    payload = {
        "source_service": "lotus-performance",
        "contract_version": "v1",
        "execution_mode": "async",
        "status": "pending",
        "result_path": "/integration/returns/series/results/example",
    }

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_benchmark_readiness_evidence(_benchmark_readiness_request())

    assert exc_info.value.code == "performance_returns_series_pending"


def test_lotus_performance_adapter_maps_missing_metadata_to_source_unavailable() -> None:
    payload = _payload()
    payload.pop("metadata")

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_metadata_missing"


def test_lotus_performance_adapter_maps_missing_generated_at_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("generated_at")

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_generated_at_missing"


def test_lotus_performance_adapter_maps_naive_generated_at_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["generated_at"] = "2026-06-21T10:00:00"

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_generated_at_naive"


def test_lotus_performance_adapter_maps_missing_as_of_date_to_source_unavailable() -> None:
    payload = _payload()
    payload.pop("as_of_date")

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_as_of_date_missing"


def test_lotus_performance_adapter_maps_missing_content_hash_to_source_unavailable() -> None:
    payload = _payload()
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    provenance.clear()

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_content_hash_missing"


def test_lotus_performance_adapter_maps_malformed_active_return_to_source_unavailable() -> None:
    payload = _payload()
    series = payload["series"]
    assert isinstance(series, dict)
    series["cumulative_active_returns"][-1]["return_value"] = "not-decimal"

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_active_return_malformed"


def test_lotus_performance_adapter_maps_malformed_active_return_point_to_unavailable() -> None:
    payload = _payload()
    series = payload["series"]
    assert isinstance(series, dict)
    series["cumulative_active_returns"][-1] = "not-object"

    with pytest.raises(PerformanceSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_underperformance_evidence(_request())

    assert exc_info.value.code == "performance_cumulative_active_return_missing"


def test_lotus_performance_adapter_accepts_missing_active_return_value_as_source_gap() -> None:
    payload = _payload()
    series = payload["series"]
    assert isinstance(series, dict)
    series["cumulative_active_returns"][-1].pop("return_value")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.source_reported_active_return is None


def test_lotus_performance_adapter_maps_stale_warning_to_stale_source_ref() -> None:
    payload = _payload()
    diagnostics = payload["diagnostics"]
    assert isinstance(diagnostics, dict)
    diagnostics["warnings"] = ["stale benchmark observation retained by source policy"]

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.performance_ref is not None
    assert evidence.performance_ref.freshness is EvidenceFreshness.STALE


def test_lotus_performance_adapter_marks_quality_unknown_without_diagnostics() -> None:
    payload = _payload()
    payload.pop("diagnostics")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.performance_ref is not None
    assert evidence.performance_ref.data_quality_status == "unknown"
    assert evidence.performance_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_performance_adapter_marks_quality_unknown_without_coverage() -> None:
    payload = _payload(extra={"diagnostics": {"warnings": []}})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.performance_ref is not None
    assert evidence.performance_ref.data_quality_status == "unknown"
    assert evidence.performance_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_performance_adapter_marks_quality_partial_when_points_are_missing() -> None:
    payload = _payload()
    diagnostics = payload["diagnostics"]
    assert isinstance(diagnostics, dict)
    coverage = diagnostics["coverage"]
    assert isinstance(coverage, dict)
    coverage["missing_points"] = 3

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_underperformance_evidence(_request())

    assert evidence.performance_ref is not None
    assert evidence.performance_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.performance_ref.data_quality_status == "partial"


def test_performance_underperformance_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        PerformanceUnderperformanceEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            active_return_threshold=Decimal("-0.005"),
        )


def test_performance_underperformance_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        PerformanceUnderperformanceEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            active_return_threshold=Decimal("-0.005"),
        )


def test_performance_benchmark_readiness_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        PerformanceBenchmarkReadinessEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_performance_benchmark_readiness_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        PerformanceBenchmarkReadinessEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )


def _benchmark_readiness_request() -> PerformanceBenchmarkReadinessEvidenceRequest:
    return PerformanceBenchmarkReadinessEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        reporting_currency="USD",
        correlation_id="corr-performance",
        trace_id="trace-performance",
    )
