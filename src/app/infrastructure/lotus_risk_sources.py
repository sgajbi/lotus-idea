from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


PRODUCT_VERSION = "v1"
CONCENTRATION_PRODUCT_ID = "lotus-risk:ConcentrationRiskReport:v1"
CONCENTRATION_ROUTE = "/analytics/risk/concentration"


@dataclass(frozen=True)
class _ConcentrationMeasures:
    top_position_weight_current: Decimal | None
    top_issuer_weight_current: Decimal | None
    issuer_coverage_status: str | None


class LotusRiskConcentrationSourceAdapter:
    def __init__(self, risk_client: DownstreamJsonClient) -> None:
        self._risk_client = risk_client

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
        freshness=_freshness(metadata, payload, supportability_state=supportability_state),
    )


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


def _freshness(
    *payloads: dict[str, Any],
    supportability_state: str,
) -> EvidenceFreshness:
    for payload in payloads:
        freshness_value = (
            payload.get("freshness")
            or payload.get("freshness_status")
            or payload.get("freshnessStatus")
        )
        if isinstance(freshness_value, str):
            normalized = freshness_value.lower()
            if "stale" in normalized:
                return EvidenceFreshness.STALE
            if "expired" in normalized:
                return EvidenceFreshness.EXPIRED
            if "unavailable" in normalized:
                return EvidenceFreshness.UNAVAILABLE
            if "current" in normalized:
                return EvidenceFreshness.CURRENT
    if supportability_state.lower() == "ready":
        return EvidenceFreshness.CURRENT
    return EvidenceFreshness.UNAVAILABLE


def _diagnostic(measures: _ConcentrationMeasures) -> str:
    if measures.issuer_coverage_status is None:
        return "risk_issuer_coverage_missing"
    if measures.top_position_weight_current is None and measures.top_issuer_weight_current is None:
        return "risk_concentration_weights_missing"
    return f"risk_issuer_coverage_{measures.issuer_coverage_status.lower()}"
