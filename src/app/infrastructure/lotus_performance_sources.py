from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.performance_sources import (
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


PRODUCT_VERSION = "v1"
RETURNS_SERIES_PRODUCT_ID = "lotus-performance:ReturnsSeriesBundle:v1"
RETURNS_SERIES_ROUTE = "/integration/returns/series"


@dataclass(frozen=True)
class _UnderperformanceMeasures:
    source_reported_active_return: Decimal | None
    benchmark_context_available: bool
    diagnostic: str


class LotusPerformanceUnderperformanceSourceAdapter:
    def __init__(self, performance_client: DownstreamJsonClient) -> None:
        self._performance_client = performance_client

    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        try:
            payload = self._performance_client.post_json(
                RETURNS_SERIES_ROUTE,
                json_payload=_returns_series_request_payload(request),
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise PerformanceSourceEntitlementDenied from exc
            raise PerformanceSourceUnavailable(code=exc.code) from exc

        measures = _underperformance_measures(payload)
        return PerformanceUnderperformanceEvidence(
            source_reported_active_return=measures.source_reported_active_return,
            benchmark_context_available=measures.benchmark_context_available,
            performance_ref=_source_ref(payload),
            performance_diagnostic=measures.diagnostic,
        )


def _returns_series_request_payload(
    request: PerformanceUnderperformanceEvidenceRequest,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "portfolio_id": request.portfolio_id,
        "as_of_date": request.as_of_date.isoformat(),
        "window": {"mode": "RELATIVE", "period": request.period_name},
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
    }
    if request.reporting_currency:
        payload["reporting_currency"] = request.reporting_currency
    return payload


def _underperformance_measures(payload: dict[str, Any]) -> _UnderperformanceMeasures:
    if str(payload.get("source_service", "")).lower() != "lotus-performance":
        raise PerformanceSourceUnavailable(code="performance_source_service_mismatch")
    if _is_async_accepted(payload):
        raise PerformanceSourceUnavailable(code="performance_returns_series_pending")

    series = _object_field(payload, "series")
    cumulative_active_returns = series.get("cumulative_active_returns")
    active_return = _last_return_value(
        cumulative_active_returns,
        code="performance_cumulative_active_return_missing",
    )
    benchmark_context_available = isinstance(payload.get("benchmark_context"), dict)
    diagnostic = (
        "performance_benchmark_context_ready"
        if benchmark_context_available
        else "performance_benchmark_context_missing"
    )
    return _UnderperformanceMeasures(
        source_reported_active_return=active_return,
        benchmark_context_available=benchmark_context_available,
        diagnostic=diagnostic,
    )


def _source_ref(payload: dict[str, Any]) -> SourceRef:
    metadata = _object_field(payload, "metadata")
    provenance = _object_field(payload, "provenance")
    return SourceRef(
        product_id=RETURNS_SERIES_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_PERFORMANCE,
        product_version=str(payload.get("contract_version") or PRODUCT_VERSION),
        route=RETURNS_SERIES_ROUTE,
        as_of_date=_date_field(payload, keys=("as_of_date", "asOfDate")),
        generated_at_utc=_datetime_field(metadata, keys=("generated_at", "generatedAt")),
        content_hash=_content_hash(provenance),
        data_quality_status=_data_quality_status(payload),
        freshness=_freshness(payload),
    )


def _is_async_accepted(payload: dict[str, Any]) -> bool:
    execution_mode = payload.get("execution_mode")
    status = payload.get("status")
    return execution_mode == "async" or status == "pending"


def _object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    raise PerformanceSourceUnavailable(code=f"performance_{key}_missing")


def _last_return_value(value: Any, *, code: str) -> Decimal | None:
    if not isinstance(value, list) or not value:
        return None
    last_point = value[-1]
    if not isinstance(last_point, dict):
        raise PerformanceSourceUnavailable(code=code)
    raw_return = last_point.get("return_value")
    if raw_return is None:
        return None
    try:
        return Decimal(str(raw_return))
    except InvalidOperation as exc:
        raise PerformanceSourceUnavailable(code="performance_active_return_malformed") from exc


def _datetime_field(payload: dict[str, Any], *, keys: tuple[str, ...]) -> datetime:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise PerformanceSourceUnavailable(code="performance_generated_at_naive")
            return parsed
    raise PerformanceSourceUnavailable(code="performance_generated_at_missing")


def _date_field(payload: dict[str, Any], *, keys: tuple[str, ...]) -> date:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return date.fromisoformat(value)
    raise PerformanceSourceUnavailable(code="performance_as_of_date_missing")


def _content_hash(provenance: dict[str, Any]) -> str:
    value = provenance.get("calculation_hash") or provenance.get("input_fingerprint")
    if isinstance(value, str) and value.strip():
        return value if value.startswith("sha256:") else f"sha256:{value}"
    raise PerformanceSourceUnavailable(code="performance_content_hash_missing")


def _data_quality_status(payload: dict[str, Any]) -> str:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return "unknown"
    coverage = diagnostics.get("coverage")
    if not isinstance(coverage, dict):
        return "unknown"
    missing_points = coverage.get("missing_points")
    if missing_points in {0, "0"}:
        return "ready"
    return "partial"


def _freshness(payload: dict[str, Any]) -> EvidenceFreshness:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return EvidenceFreshness.UNAVAILABLE
    warnings = diagnostics.get("warnings")
    if isinstance(warnings, list) and any("stale" in str(warning).lower() for warning in warnings):
        return EvidenceFreshness.STALE
    return EvidenceFreshness.CURRENT
