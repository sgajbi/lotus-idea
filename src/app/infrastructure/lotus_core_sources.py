from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


PRODUCT_VERSION = "v1"
PORTFOLIO_STATE_PRODUCT_ID = "lotus-core:PortfolioStateSnapshot:v1"
HOLDINGS_PRODUCT_ID = "lotus-core:HoldingsAsOf:v1"
CASH_MOVEMENT_PRODUCT_ID = "lotus-core:PortfolioCashMovementSummary:v1"
CASHFLOW_PROJECTION_PRODUCT_ID = "lotus-core:PortfolioCashflowProjection:v1"


@dataclass(frozen=True)
class _CashWeightEvidence:
    value: Decimal | None
    diagnostic: str


class LotusCoreHighCashSourceAdapter:
    def __init__(
        self,
        query_client: DownstreamJsonClient,
        query_control_plane_client: DownstreamJsonClient | None = None,
    ) -> None:
        self._query_client = query_client
        self._query_control_plane_client = query_control_plane_client or query_client

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        portfolio_ref = quote(request.portfolio_id, safe="")
        as_of = request.as_of_date.isoformat()
        try:
            portfolio_state_payload = self._query_control_plane_client.post_json(
                f"/integration/portfolios/{portfolio_ref}/core-snapshot",
                json_payload={
                    "as_of_date": as_of,
                    "snapshot_mode": "BASELINE",
                    "consumer_system": "lotus-idea",
                    "tenant_id": "default",
                    "sections": ["portfolio_totals"],
                },
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
            holdings_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/cash-balances?as_of_date={as_of}",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
            cash_movement_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/cash-movement-summary?start_date={as_of}&end_date={as_of}",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
            cashflow_projection_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/cashflow-projection?as_of_date={as_of}&horizon_days=30&include_projected=true",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise CoreSourceEntitlementDenied from exc
            raise CoreSourceUnavailable(code=exc.code) from exc

        cash_weight_evidence = _source_reported_cash_weight(holdings_payload)
        return CoreHighCashEvidence(
            source_reported_cash_weight=cash_weight_evidence.value,
            portfolio_state_ref=_source_ref(
                portfolio_state_payload,
                product_id=PORTFOLIO_STATE_PRODUCT_ID,
                route="/integration/portfolios/{portfolio_id}/core-snapshot",
            ),
            holdings_ref=_source_ref(
                holdings_payload,
                product_id=HOLDINGS_PRODUCT_ID,
                route="/portfolios/{portfolio_id}/cash-balances",
            ),
            cash_movement_ref=_source_ref(
                cash_movement_payload,
                product_id=CASH_MOVEMENT_PRODUCT_ID,
                route="/portfolios/{portfolio_id}/cash-movement-summary",
            ),
            cashflow_projection_ref=_source_ref(
                cashflow_projection_payload,
                product_id=CASHFLOW_PROJECTION_PRODUCT_ID,
                route="/portfolios/{portfolio_id}/cashflow-projection",
            ),
            cash_weight_diagnostic=cash_weight_evidence.diagnostic,
        )


def _source_reported_cash_weight(payload: dict[str, Any]) -> _CashWeightEvidence:
    for cash_weight_payload in _cash_weight_payloads(payload):
        supportability = _cash_weight_supportability(cash_weight_payload)
        if supportability is not None and supportability != "SUPPORTED":
            return _CashWeightEvidence(
                value=None,
                diagnostic=f"core_cash_weight_{supportability.lower()}",
            )
        for key in (
            "source_reported_cash_weight",
            "sourceReportedCashWeight",
            "cash_weight",
            "cashWeight",
        ):
            if key not in cash_weight_payload:
                continue
            try:
                value = cash_weight_payload[key]
                return _CashWeightEvidence(
                    value=Decimal(str(value)) if value is not None else None,
                    diagnostic=(
                        "core_cash_weight_supported"
                        if value is not None
                        else "core_cash_weight_missing"
                    ),
                )
            except InvalidOperation as exc:
                raise CoreSourceUnavailable(code="core_cash_weight_malformed") from exc
    return _CashWeightEvidence(value=None, diagnostic="core_cash_weight_missing")


def _cash_weight_payloads(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    totals = payload.get("totals")
    if isinstance(totals, dict):
        return (payload, totals)
    return (payload,)


def _cash_weight_supportability(payload: dict[str, Any]) -> str | None:
    for key in (
        "source_reported_cash_weight_supportability",
        "sourceReportedCashWeightSupportability",
        "cash_weight_supportability",
        "cashWeightSupportability",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


def _source_ref(payload: dict[str, Any], *, product_id: str, route: str) -> SourceRef:
    generated_at = _datetime_field(payload, "generated_at", "generatedAt")
    as_of_date = _date_field(payload, "as_of_date", "asOfDate", "resolved_as_of_date")
    content_hash = _content_hash(payload)
    data_quality_status = str(
        payload.get("data_quality_status") or payload.get("dataQualityStatus") or "unknown"
    )
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version=str(
            payload.get("product_version") or payload.get("productVersion") or PRODUCT_VERSION
        ),
        route=route,
        as_of_date=as_of_date,
        generated_at_utc=generated_at,
        content_hash=content_hash,
        data_quality_status=data_quality_status,
        freshness=_freshness(payload, generated_at=generated_at),
    )


def _datetime_field(payload: dict[str, Any], *keys: str) -> datetime:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise CoreSourceUnavailable(code="core_generated_at_naive")
            return parsed
    raise CoreSourceUnavailable(code="core_generated_at_missing")


def _date_field(payload: dict[str, Any], *keys: str) -> date:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return date.fromisoformat(value)
    raise CoreSourceUnavailable(code="core_as_of_date_missing")


def _content_hash(payload: dict[str, Any]) -> str:
    for key in (
        "source_batch_fingerprint",
        "sourceBatchFingerprint",
        "snapshot_id",
        "snapshotId",
        "request_fingerprint",
        "requestFingerprint",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value if value.startswith("sha256:") else f"sha256:{value}"
    raise CoreSourceUnavailable(code="core_content_hash_missing")


def _freshness(payload: dict[str, Any], *, generated_at: datetime) -> EvidenceFreshness:
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
    return EvidenceFreshness.CURRENT
