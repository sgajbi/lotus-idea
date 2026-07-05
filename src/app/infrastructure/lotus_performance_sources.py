from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import time
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.infrastructure.source_product_payloads import first_reason_code
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceMandateHealthContextEvidence,
    PerformanceMandateHealthContextRequest,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


PRODUCT_VERSION = "v1"
RETURNS_SERIES_PRODUCT_ID = "lotus-performance:ReturnsSeriesBundle:v1"
RETURNS_SERIES_ROUTE = "/integration/returns/series"
ASYNC_RESULT_MAX_POLLS = 10
ASYNC_RESULT_POLL_INTERVAL_SECONDS = 0.25
MANDATE_PERFORMANCE_HEALTH_PRODUCT_ID = "lotus-performance:MandatePerformanceHealthContext:v1"
MANDATE_PERFORMANCE_HEALTH_ROUTE = "/performance/mandate-health-context"


@dataclass(frozen=True)
class _UnderperformanceMeasures:
    source_reported_active_return: Decimal | None
    benchmark_context_available: bool
    diagnostic: str


@dataclass(frozen=True)
class _BenchmarkReadinessMeasures:
    benchmark_context_available: bool
    diagnostic: str


class LotusPerformanceUnderperformanceSourceAdapter:
    def __init__(
        self,
        performance_client: DownstreamJsonClient,
        *,
        async_result_max_polls: int = ASYNC_RESULT_MAX_POLLS,
        async_result_poll_interval_seconds: float = ASYNC_RESULT_POLL_INTERVAL_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if async_result_max_polls < 1:
            raise ValueError("async_result_max_polls must be at least 1")
        if async_result_poll_interval_seconds < 0:
            raise ValueError("async_result_poll_interval_seconds must not be negative")
        self._performance_client = performance_client
        self._async_result_max_polls = async_result_max_polls
        self._async_result_poll_interval_seconds = async_result_poll_interval_seconds
        self._sleep = sleep

    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        payload = self._fetch_returns_series_payload(request)
        measures = _underperformance_measures(payload)
        return PerformanceUnderperformanceEvidence(
            source_reported_active_return=measures.source_reported_active_return,
            benchmark_context_available=measures.benchmark_context_available,
            performance_ref=_source_ref(payload),
            performance_diagnostic=measures.diagnostic,
        )

    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        payload = self._fetch_returns_series_payload(request)
        measures = _benchmark_readiness_measures(payload)
        return PerformanceBenchmarkReadinessEvidence(
            benchmark_context_available=measures.benchmark_context_available,
            performance_ref=_source_ref(payload),
            performance_diagnostic=measures.diagnostic,
        )

    def _fetch_returns_series_payload(
        self,
        request: PerformanceUnderperformanceEvidenceRequest
        | PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> dict[str, Any]:
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

        if _is_async_accepted(payload):
            return self._resolve_returns_series_result(payload, request)
        return payload

    def _resolve_returns_series_result(
        self,
        accepted_payload: dict[str, Any],
        request: PerformanceUnderperformanceEvidenceRequest
        | PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> dict[str, Any]:
        result_path = _result_path(accepted_payload)
        last_payload = accepted_payload
        for attempt_index in range(self._async_result_max_polls):
            try:
                result_payload = self._performance_client.get_json(
                    result_path,
                    correlation_id=request.correlation_id,
                    trace_id=request.trace_id,
                )
            except DownstreamServiceError as exc:
                if exc.status_code == 404 and attempt_index < self._async_result_max_polls - 1:
                    self._sleep_between_async_polls()
                    continue
                if exc.status_code in {401, 403}:
                    raise PerformanceSourceEntitlementDenied from exc
                raise PerformanceSourceUnavailable(code=exc.code) from exc

            last_payload = result_payload
            if not _is_async_accepted(result_payload):
                return result_payload
            if attempt_index < self._async_result_max_polls - 1:
                self._sleep_between_async_polls()

        if _is_async_accepted(last_payload):
            raise PerformanceSourceUnavailable(code="performance_returns_series_pending")
        return last_payload

    def _sleep_between_async_polls(self) -> None:
        if self._async_result_poll_interval_seconds > 0:
            self._sleep(self._async_result_poll_interval_seconds)

    def fetch_mandate_health_context(
        self,
        request: PerformanceMandateHealthContextRequest,
    ) -> PerformanceMandateHealthContextEvidence:
        try:
            payload = self._performance_client.post_json(
                MANDATE_PERFORMANCE_HEALTH_ROUTE,
                json_payload=_mandate_health_request_payload(request),
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise PerformanceSourceEntitlementDenied from exc
            raise PerformanceSourceUnavailable(code=exc.code) from exc

        _validate_mandate_health_payload(payload)
        return PerformanceMandateHealthContextEvidence(
            mandate_performance_health_ref=_mandate_health_source_ref(payload, request),
            health_state=_text_field(payload, "health_state"),
            threshold_breached=_optional_bool_field(payload, "threshold_breached"),
            performance_diagnostic=first_reason_code(payload),
        )


def _returns_series_request_payload(
    request: PerformanceUnderperformanceEvidenceRequest
    | PerformanceBenchmarkReadinessEvidenceRequest,
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


def _mandate_health_request_payload(
    request: PerformanceMandateHealthContextRequest,
) -> dict[str, Any]:
    return {
        "portfolio_id": request.portfolio_id,
        "as_of_date": request.as_of_date.isoformat(),
        "period_name": request.period_name,
        "portfolio_period_return": _decimal_text(request.portfolio_period_return),
        "benchmark_period_return": _decimal_text(request.benchmark_period_return),
        "active_return_attention_threshold": str(request.active_return_attention_threshold),
    }


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


def _benchmark_readiness_measures(payload: dict[str, Any]) -> _BenchmarkReadinessMeasures:
    if str(payload.get("source_service", "")).lower() != "lotus-performance":
        raise PerformanceSourceUnavailable(code="performance_source_service_mismatch")
    if _is_async_accepted(payload):
        raise PerformanceSourceUnavailable(code="performance_returns_series_pending")

    benchmark_context_available = isinstance(payload.get("benchmark_context"), dict)
    diagnostic = (
        "performance_benchmark_context_ready"
        if benchmark_context_available
        else "performance_benchmark_context_missing"
    )
    return _BenchmarkReadinessMeasures(
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


def _mandate_health_source_ref(
    payload: dict[str, Any],
    request: PerformanceMandateHealthContextRequest,
) -> SourceRef:
    return SourceRef(
        product_id=MANDATE_PERFORMANCE_HEALTH_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_PERFORMANCE,
        product_version=_text_field(payload, "product_version"),
        route=MANDATE_PERFORMANCE_HEALTH_ROUTE,
        as_of_date=_date_field(payload, keys=("as_of_date", "asOfDate")),
        generated_at_utc=request.evaluated_at_utc,
        content_hash=_content_hash(payload),
        data_quality_status=_text_field(payload, "health_state"),
        freshness=EvidenceFreshness.UNAVAILABLE,
    )


def _validate_mandate_health_payload(payload: dict[str, Any]) -> None:
    if _text_field(payload, "product_name") != "MandatePerformanceHealthContext":
        raise PerformanceSourceUnavailable(code="performance_mandate_health_product_mismatch")
    source_services = payload.get("source_services") or payload.get("sourceServices")
    if not isinstance(source_services, list) or "lotus-performance" not in source_services:
        raise PerformanceSourceUnavailable(code="performance_mandate_health_source_mismatch")


def _is_async_accepted(payload: dict[str, Any]) -> bool:
    execution_mode = payload.get("execution_mode")
    status = payload.get("status")
    return execution_mode == "async" or status == "pending"


def _result_path(payload: dict[str, Any]) -> str:
    value = payload.get("result_path")
    if isinstance(value, str) and value.startswith("/"):
        return value
    raise PerformanceSourceUnavailable(code="performance_returns_series_result_path_missing")


def _object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    raise PerformanceSourceUnavailable(code=f"performance_{key}_missing")


def _text_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise PerformanceSourceUnavailable(code=f"performance_{key}_missing")


def _optional_bool_field(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


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
    value = (
        provenance.get("calculation_hash")
        or provenance.get("input_fingerprint")
        or provenance.get("request_fingerprint")
        or provenance.get("requestFingerprint")
    )
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
    for candidate in (payload, diagnostics):
        freshness_value = (
            candidate.get("freshness")
            or candidate.get("freshness_status")
            or candidate.get("freshnessStatus")
            or candidate.get("freshness_bucket")
            or candidate.get("freshnessBucket")
        )
        if isinstance(freshness_value, str):
            normalized = freshness_value.lower()
            if "stale" in normalized:
                return EvidenceFreshness.STALE
            if "expired" in normalized:
                return EvidenceFreshness.EXPIRED
            if "unavailable" in normalized or "missing" in normalized:
                return EvidenceFreshness.UNAVAILABLE
            if "current" in normalized or "same_day" in normalized:
                return EvidenceFreshness.CURRENT
    return EvidenceFreshness.UNAVAILABLE
