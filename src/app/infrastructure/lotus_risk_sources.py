from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.infrastructure.source_product_payloads import first_reason_code
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskMandateHealthContextEvidence,
    RiskMandateHealthContextRequest,
    RiskReturnObservation,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)


PRODUCT_VERSION = "v1"
CONCENTRATION_PRODUCT_ID = "lotus-risk:ConcentrationRiskReport:v1"
CONCENTRATION_ROUTE = "/analytics/risk/concentration"
RISK_METRICS_PRODUCT_ID = "lotus-risk:RiskMetricsReport:v1"
RISK_CALCULATE_ROUTE = "/analytics/risk/calculate"
DRAWDOWN_PRODUCT_ID = "lotus-risk:DrawdownAnalyticsReport:v1"
DRAWDOWN_ROUTE = "/analytics/risk/drawdown"
MANDATE_RISK_HEALTH_PRODUCT_ID = "lotus-risk:MandateRiskHealthContext:v1"
MANDATE_RISK_HEALTH_ROUTE = "/analytics/risk/mandate-health-context"


@dataclass(frozen=True)
class _ConcentrationMeasures:
    top_position_weight_current: Decimal | None
    top_issuer_weight_current: Decimal | None
    issuer_coverage_status: str | None


@dataclass(frozen=True)
class _VolatilityMeasures:
    source_reported_volatility: Decimal | None
    supportability_state: str | None
    diagnostic: str


@dataclass(frozen=True)
class _DrawdownMeasures:
    source_reported_max_drawdown: Decimal | None
    supportability_state: str | None
    diagnostic: str


class LotusRiskConcentrationSourceAdapter:
    def __init__(self, risk_client: DownstreamJsonClient) -> None:
        self._risk_client = risk_client

    def close(self) -> None:
        self._risk_client.close()

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        try:
            payload = self._risk_client.post_json(
                CONCENTRATION_ROUTE,
                json_payload={
                    "input_mode": "stateful",
                    "stateful_input": {
                        "portfolio_id": request.portfolio_id,
                        "as_of_date": request.as_of_date.isoformat(),
                    },
                },
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise RiskSourceEntitlementDenied from exc
            raise RiskSourceUnavailable(code=exc.code) from exc

        measures = _concentration_measures(payload)
        return RiskConcentrationEvidence(
            top_position_weight_current=measures.top_position_weight_current,
            top_issuer_weight_current=measures.top_issuer_weight_current,
            issuer_coverage_status=measures.issuer_coverage_status,
            concentration_ref=_source_ref(payload),
            concentration_diagnostic=_diagnostic(measures),
        )


class LotusRiskVolatilitySourceAdapter:
    def __init__(self, risk_client: DownstreamJsonClient) -> None:
        self._risk_client = risk_client

    def close(self) -> None:
        self._risk_client.close()

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        try:
            payload = self._risk_client.post_json(
                RISK_CALCULATE_ROUTE,
                json_payload=_risk_calculate_request_payload(request),
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise RiskSourceEntitlementDenied from exc
            raise RiskSourceUnavailable(code=exc.code) from exc

        measures = _volatility_measures(payload, period_name=request.period_name)
        return RiskVolatilityEvidence(
            source_reported_volatility=measures.source_reported_volatility,
            risk_supportability_state=measures.supportability_state,
            risk_ref=_risk_metrics_source_ref(payload),
            risk_diagnostic=measures.diagnostic,
        )


class LotusRiskDrawdownSourceAdapter:
    def __init__(self, risk_client: DownstreamJsonClient) -> None:
        self._risk_client = risk_client

    def close(self) -> None:
        self._risk_client.close()

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        try:
            payload = self._risk_client.post_json(
                DRAWDOWN_ROUTE,
                json_payload=_drawdown_request_payload(request),
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise RiskSourceEntitlementDenied from exc
            raise RiskSourceUnavailable(code=exc.code) from exc

        measures = _drawdown_measures(payload, period_name=request.period_name)
        return RiskDrawdownEvidence(
            source_reported_max_drawdown=measures.source_reported_max_drawdown,
            risk_supportability_state=measures.supportability_state,
            risk_ref=_drawdown_source_ref(payload),
            risk_diagnostic=measures.diagnostic,
        )


class LotusRiskMandateHealthSourceAdapter:
    def __init__(self, risk_client: DownstreamJsonClient) -> None:
        self._risk_client = risk_client

    def fetch_mandate_health_context(
        self, request: RiskMandateHealthContextRequest
    ) -> RiskMandateHealthContextEvidence:
        try:
            payload = self._risk_client.post_json(
                MANDATE_RISK_HEALTH_ROUTE,
                json_payload=_mandate_health_request_payload(request),
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise RiskSourceEntitlementDenied from exc
            raise RiskSourceUnavailable(code=exc.code) from exc

        _validate_mandate_health_payload(payload)
        return RiskMandateHealthContextEvidence(
            mandate_risk_health_ref=_mandate_health_source_ref(payload, request),
            health_state=_required_text_field(payload, "health_state"),
            threshold_breached=_optional_bool_field(payload, "threshold_breached"),
            risk_diagnostic=first_reason_code(payload),
        )


def _risk_calculate_request_payload(request: RiskVolatilityEvidenceRequest) -> dict[str, Any]:
    return {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": request.portfolio_id,
            "as_of_date": request.as_of_date.isoformat(),
            "periods": [{"type": request.period_name, "name": request.period_name}],
            "metrics": ["VOLATILITY"],
        },
    }


def _drawdown_request_payload(request: RiskDrawdownEvidenceRequest) -> dict[str, Any]:
    return {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": request.portfolio_id,
            "as_of_date": request.as_of_date.isoformat(),
            "periods": [{"type": request.period_name, "name": request.period_name}],
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
    }


def _mandate_health_request_payload(request: RiskMandateHealthContextRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "portfolio_id": request.portfolio_id,
        "scope": {
            "as_of_date": request.as_of_date.isoformat(),
            "net_or_gross": request.net_or_gross,
        },
        "period": {"type": request.period_name, "name": request.period_name},
        "portfolio_open_date": request.portfolio_open_date.isoformat(),
        "returns": _return_observations(request.returns),
        "benchmark_returns": _return_observations(request.benchmark_returns),
        "tracking_error_attention_threshold": str(request.tracking_error_attention_threshold),
    }
    if request.reporting_currency:
        scope = payload["scope"]
        assert isinstance(scope, dict)
        scope["reporting_currency"] = request.reporting_currency
    return payload


def _volatility_measures(payload: dict[str, Any], *, period_name: str) -> _VolatilityMeasures:
    results = _object_field(payload, "results")
    period_result = _object_field(results, period_name)
    metrics = _object_field(period_result, "metrics")
    volatility_metric = _object_field(metrics, "VOLATILITY")
    metadata = _object_field(payload, "metadata")
    supportability_state = _supportability_state(metadata)
    volatility = _decimal_field(
        volatility_metric,
        "value",
        code="risk_volatility_value_malformed",
    )
    if volatility is None:
        return _VolatilityMeasures(
            source_reported_volatility=None,
            supportability_state=supportability_state,
            diagnostic="risk_volatility_value_missing",
        )
    diagnostic = (
        "risk_volatility_source_ready"
        if supportability_state == "ready"
        else f"risk_volatility_source_{supportability_state or 'unknown'}"
    )
    return _VolatilityMeasures(
        source_reported_volatility=volatility,
        supportability_state=supportability_state,
        diagnostic=diagnostic,
    )


def _drawdown_measures(payload: dict[str, Any], *, period_name: str) -> _DrawdownMeasures:
    results = _object_field(payload, "results")
    period_result = _object_field(results, period_name)
    summary = _object_field(period_result, "summary")
    metadata = _object_field(payload, "metadata")
    supportability_state = _supportability_state(metadata)
    max_drawdown = _decimal_field(
        summary,
        "max_drawdown",
        code="risk_drawdown_value_malformed",
    )
    if max_drawdown is None:
        return _DrawdownMeasures(
            source_reported_max_drawdown=None,
            supportability_state=supportability_state,
            diagnostic="risk_drawdown_value_missing",
        )
    diagnostic = (
        "risk_drawdown_source_ready"
        if supportability_state == "ready"
        else f"risk_drawdown_source_{supportability_state or 'unknown'}"
    )
    return _DrawdownMeasures(
        source_reported_max_drawdown=max_drawdown,
        supportability_state=supportability_state,
        diagnostic=diagnostic,
    )


def _concentration_measures(payload: dict[str, Any]) -> _ConcentrationMeasures:
    single_position = _object_field(payload, "single_position_concentration")
    issuer_concentration = _object_field(payload, "issuer_concentration")
    return _ConcentrationMeasures(
        top_position_weight_current=_decimal_field(
            single_position,
            "top_position_weight_current",
            code="risk_top_position_weight_malformed",
        ),
        top_issuer_weight_current=_decimal_field(
            issuer_concentration,
            "top_issuer_weight_current",
            code="risk_top_issuer_weight_malformed",
        ),
        issuer_coverage_status=_text_field(issuer_concentration, "coverage_status"),
    )


def _source_ref(payload: dict[str, Any]) -> SourceRef:
    metadata = _object_field(payload, "metadata")
    generated_at = _datetime_field(
        metadata,
        payload,
        keys=("generated_at", "generatedAt", "calculated_at", "calculatedAt"),
    )
    as_of_date = _date_field(metadata, payload, keys=("as_of_date", "asOfDate"))
    content_hash = _content_hash(metadata, payload)
    calculation_supportability = metadata.get("calculation_supportability")
    supportability_state = (
        str(calculation_supportability.get("state"))
        if isinstance(calculation_supportability, dict)
        else "unknown"
    )
    return SourceRef(
        product_id=CONCENTRATION_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_RISK,
        product_version=str(
            metadata.get("product_version")
            or metadata.get("productVersion")
            or payload.get("product_version")
            or PRODUCT_VERSION
        ),
        route=CONCENTRATION_ROUTE,
        as_of_date=as_of_date,
        generated_at_utc=generated_at,
        content_hash=content_hash,
        data_quality_status=supportability_state,
        freshness=_freshness(metadata, payload),
    )


def _drawdown_source_ref(payload: dict[str, Any]) -> SourceRef:
    metadata = _object_field(payload, "metadata")
    scope = _object_field(payload, "scope")
    supportability_state = _supportability_state(metadata) or "unknown"
    return SourceRef(
        product_id=DRAWDOWN_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_RISK,
        product_version=str(
            metadata.get("contract_version")
            or metadata.get("contractVersion")
            or metadata.get("product_version")
            or metadata.get("productVersion")
            or PRODUCT_VERSION
        ),
        route=DRAWDOWN_ROUTE,
        as_of_date=_date_field(scope, metadata, keys=("as_of_date", "asOfDate")),
        generated_at_utc=_datetime_field(
            metadata,
            keys=("generated_at", "generatedAt", "calculated_at", "calculatedAt"),
        ),
        content_hash=_content_hash(metadata, payload),
        data_quality_status=supportability_state,
        freshness=_freshness(metadata, payload),
    )


def _risk_metrics_source_ref(payload: dict[str, Any]) -> SourceRef:
    metadata = _object_field(payload, "metadata")
    scope = _object_field(payload, "scope")
    supportability_state = _supportability_state(metadata) or "unknown"
    return SourceRef(
        product_id=RISK_METRICS_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_RISK,
        product_version=str(
            metadata.get("contract_version")
            or metadata.get("contractVersion")
            or metadata.get("product_version")
            or metadata.get("productVersion")
            or PRODUCT_VERSION
        ),
        route=RISK_CALCULATE_ROUTE,
        as_of_date=_date_field(scope, metadata, keys=("as_of_date", "asOfDate")),
        generated_at_utc=_datetime_field(
            metadata,
            keys=("generated_at", "generatedAt", "calculated_at", "calculatedAt"),
        ),
        content_hash=_content_hash(metadata, payload),
        data_quality_status=supportability_state,
        freshness=_freshness(metadata, payload),
    )


def _mandate_health_source_ref(
    payload: dict[str, Any],
    request: RiskMandateHealthContextRequest,
) -> SourceRef:
    return SourceRef(
        product_id=MANDATE_RISK_HEALTH_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_RISK,
        product_version=_required_text_field(payload, "product_version"),
        route=MANDATE_RISK_HEALTH_ROUTE,
        as_of_date=_date_field(payload, keys=("as_of_date", "asOfDate")),
        generated_at_utc=request.evaluated_at_utc,
        content_hash=_content_hash(payload),
        data_quality_status=_required_text_field(payload, "health_state"),
        freshness=EvidenceFreshness.UNAVAILABLE,
    )


def _validate_mandate_health_payload(payload: dict[str, Any]) -> None:
    if _text_field(payload, "product_name") != "MandateRiskHealthContext":
        raise RiskSourceUnavailable(code="risk_mandate_health_product_mismatch")
    source_services = payload.get("source_services") or payload.get("sourceServices")
    if not isinstance(source_services, list) or "lotus-risk" not in source_services:
        raise RiskSourceUnavailable(code="risk_mandate_health_source_mismatch")


def _supportability_state(metadata: dict[str, Any]) -> str | None:
    supportability = metadata.get("calculation_supportability")
    if isinstance(supportability, dict):
        state = supportability.get("state")
        if isinstance(state, str) and state.strip():
            return state.strip().lower()
    if isinstance(supportability, str) and supportability.strip():
        return supportability.strip().lower()
    return None


def _object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    raise RiskSourceUnavailable(code=f"risk_{key}_missing")


def _decimal_field(payload: dict[str, Any], key: str, *, code: str) -> Decimal | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise RiskSourceUnavailable(code=code) from exc


def _text_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _required_text_field(payload: dict[str, Any], key: str) -> str:
    value = _text_field(payload, key)
    if value is None:
        raise RiskSourceUnavailable(code=f"risk_{key}_missing")
    return value


def _optional_bool_field(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _return_observations(observations: tuple[RiskReturnObservation, ...]) -> list[dict[str, str]]:
    return [
        {
            "date": observation.observation_date.isoformat(),
            "value": str(observation.return_value),
        }
        for observation in observations
    ]


def _datetime_field(
    *payloads: dict[str, Any],
    keys: tuple[str, ...],
) -> datetime:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise RiskSourceUnavailable(code="risk_generated_at_naive")
                return parsed
    raise RiskSourceUnavailable(code="risk_generated_at_missing")


def _date_field(*payloads: dict[str, Any], keys: tuple[str, ...]) -> date:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                return date.fromisoformat(value)
    raise RiskSourceUnavailable(code="risk_as_of_date_missing")


def _content_hash(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        for key in (
            "request_fingerprint",
            "requestFingerprint",
            "source_batch_fingerprint",
            "sourceBatchFingerprint",
            "lineage_fingerprint",
            "lineageFingerprint",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value if value.startswith("sha256:") else f"sha256:{value}"
    raise RiskSourceUnavailable(code="risk_content_hash_missing")


def _freshness(*payloads: dict[str, Any]) -> EvidenceFreshness:
    for payload in payloads:
        nested_supportability = payload.get("calculation_supportability")
        candidates = [payload]
        if isinstance(nested_supportability, dict):
            candidates.append(nested_supportability)
        for candidate in candidates:
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


def _diagnostic(measures: _ConcentrationMeasures) -> str:
    if measures.issuer_coverage_status is None:
        return "risk_issuer_coverage_missing"
    if measures.top_position_weight_current is None and measures.top_issuer_weight_current is None:
        return "risk_concentration_weights_missing"
    return f"risk_issuer_coverage_{measures.issuer_coverage_status.lower()}"
