from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


PRODUCT_VERSION = "v1"
PORTFOLIO_STATE_PRODUCT_ID = "lotus-core:PortfolioStateSnapshot:v1"
HOLDINGS_PRODUCT_ID = "lotus-core:HoldingsAsOf:v1"
CASH_MOVEMENT_PRODUCT_ID = "lotus-core:PortfolioCashMovementSummary:v1"
CASHFLOW_PROJECTION_PRODUCT_ID = "lotus-core:PortfolioCashflowProjection:v1"
BENCHMARK_ASSIGNMENT_PRODUCT_ID = "lotus-core:BenchmarkAssignment:v1"
MATURITY_SUMMARY_PRODUCT_ID = "lotus-core:PortfolioMaturitySummary:v1"


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

    def close(self) -> None:
        self._query_client.close()
        if self._query_control_plane_client is not self._query_client:
            self._query_control_plane_client.close()

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

    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        portfolio_ref = quote(request.portfolio_id, safe="")
        as_of = request.as_of_date.isoformat()
        payload: dict[str, object] = {"as_of_date": as_of}
        if request.reporting_currency:
            payload["reporting_currency"] = request.reporting_currency
        try:
            assignment_payload = self._query_control_plane_client.post_json(
                f"/integration/portfolios/{portfolio_ref}/benchmark-assignment",
                json_payload=payload,
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise CoreSourceEntitlementDenied from exc
            raise CoreSourceUnavailable(code=exc.code) from exc

        assignment_status = _text_field(assignment_payload, "assignment_status", "assignmentStatus")
        benchmark_identity_resolved = (
            _text_field(
                assignment_payload,
                "benchmark_id",
                "benchmarkId",
            )
            is not None
        )
        assignment_effective_for_as_of_date = _assignment_effective_for_as_of_date(
            assignment_payload,
            request.as_of_date,
        )
        assignment_version_present = assignment_payload.get("assignment_version") is not None or (
            assignment_payload.get("assignmentVersion") is not None
        )
        return CoreBenchmarkAssignmentEvidence(
            benchmark_assignment_ref=_source_ref(
                assignment_payload,
                product_id=BENCHMARK_ASSIGNMENT_PRODUCT_ID,
                route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
            ),
            benchmark_identity_resolved=benchmark_identity_resolved,
            assignment_effective_for_as_of_date=assignment_effective_for_as_of_date,
            assignment_status=assignment_status,
            assignment_version_present=assignment_version_present,
            assignment_diagnostic=_benchmark_assignment_diagnostic(
                benchmark_identity_resolved=benchmark_identity_resolved,
                assignment_effective_for_as_of_date=assignment_effective_for_as_of_date,
                assignment_status=assignment_status,
                assignment_version_present=assignment_version_present,
            ),
        )

    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
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
                    "sections": ["portfolio_state", "portfolio_totals"],
                },
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise CoreSourceEntitlementDenied from exc
            raise CoreSourceUnavailable(code=exc.code) from exc

        return CorePortfolioStateEvidence(
            portfolio_state_ref=_source_ref(
                portfolio_state_payload,
                product_id=PORTFOLIO_STATE_PRODUCT_ID,
                route="/integration/portfolios/{portfolio_id}/core-snapshot",
            ),
            source_evidence_available=True,
            portfolio_state_diagnostic="core_portfolio_state_ready",
        )

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        portfolio_ref = quote(request.portfolio_id, safe="")
        as_of = request.as_of_date.isoformat()
        try:
            cash_movement_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/cash-movement-summary?start_date={as_of}&end_date={as_of}",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
            cashflow_projection_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/cashflow-projection?as_of_date={as_of}"
                f"&horizon_days={request.horizon_days}&include_projected=true",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise CoreSourceEntitlementDenied from exc
            raise CoreSourceUnavailable(code=exc.code) from exc

        cash_movement_count = _int_field(cash_movement_payload, "cashflow_count", "cashflowCount")
        min_projected_cumulative_cashflow = _min_projected_cumulative_cashflow(
            cashflow_projection_payload
        )
        return CoreLowIncomeEvidence(
            source_reported_min_projected_cumulative_cashflow=min_projected_cumulative_cashflow,
            cash_movement_count=cash_movement_count,
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
            cashflow_diagnostic=_low_income_cashflow_diagnostic(
                cash_movement_count=cash_movement_count,
                min_projected_cumulative_cashflow=min_projected_cumulative_cashflow,
            ),
        )

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        portfolio_ref = quote(request.portfolio_id, safe="")
        as_of = request.as_of_date.isoformat()
        try:
            maturity_summary_payload = self._query_client.get_json(
                f"/portfolios/{portfolio_ref}/maturity-summary?as_of_date={as_of}"
                f"&horizon_days={request.maturity_window_days}&include_projected=false",
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise CoreSourceEntitlementDenied from exc
            raise CoreSourceUnavailable(code=exc.code) from exc

        next_maturity_date = _explicit_next_maturity_date(maturity_summary_payload)
        maturing_position_count = _explicit_maturing_position_count(maturity_summary_payload)
        maturity_fact_ref = _source_ref(
            maturity_summary_payload,
            product_id=MATURITY_SUMMARY_PRODUCT_ID,
            route="/portfolios/{portfolio_id}/maturity-summary",
        )
        holdings_ref = _holdings_lineage_ref_or_none(maturity_summary_payload)
        if holdings_ref is None:
            raise CoreSourceUnavailable(code="core_maturity_upstream_holdings_ref_missing")
        return CoreBondMaturityEvidence(
            source_reported_next_maturity_date=next_maturity_date,
            source_reported_maturing_position_count=maturing_position_count,
            holdings_ref=holdings_ref,
            maturity_fact_ref=maturity_fact_ref,
            maturity_diagnostic=_bond_maturity_diagnostic(
                next_maturity_date_present=next_maturity_date is not None,
                maturing_position_count=maturing_position_count,
                supportability_status=_text_field(
                    maturity_summary_payload,
                    "supportability_status",
                    "supportabilityStatus",
                ),
            ),
        )


def _holdings_lineage_ref_or_none(payload: dict[str, Any]) -> SourceRef | None:
    source_product_name = _text_field(
        payload,
        "source_product_name",
        "sourceProductName",
    )
    if source_product_name != "HoldingsAsOf":
        return None
    lineage = payload.get("source_lineage") or payload.get("sourceLineage")
    upstream_hash = lineage.get("upstream_content_hash") if isinstance(lineage, dict) else None
    payload_for_ref = dict(payload)
    if isinstance(upstream_hash, str) and upstream_hash.strip():
        payload_for_ref["content_hash"] = upstream_hash
        payload_for_ref["source_batch_fingerprint"] = upstream_hash
    return _source_ref(
        payload_for_ref,
        product_id=HOLDINGS_PRODUCT_ID,
        route="/portfolios/{portfolio_id}/positions",
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


def _optional_date_field(payload: dict[str, Any], *keys: str) -> date | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return date.fromisoformat(value)
    return None


def _bond_maturity_diagnostic(
    *,
    next_maturity_date_present: bool,
    maturing_position_count: int,
    supportability_status: str | None,
) -> str:
    if supportability_status is not None and supportability_status.upper() not in {
        "SUPPORTED",
        "PARTIAL",
    }:
        return f"core_maturity_{supportability_status.lower()}"
    if not next_maturity_date_present:
        return "core_maturity_date_missing"
    if maturing_position_count < 1:
        return "core_maturity_window_empty"
    return "core_maturity_evidence_ready"


def _explicit_next_maturity_date(payload: dict[str, Any]) -> date | None:
    try:
        return _optional_date_field(
            payload,
            "source_reported_next_maturity_date",
            "sourceReportedNextMaturityDate",
            "next_maturity_date",
            "nextMaturityDate",
        )
    except ValueError as exc:
        raise CoreSourceUnavailable(code="core_maturity_date_malformed") from exc


def _explicit_maturing_position_count(payload: dict[str, Any]) -> int:
    value = _int_field(
        payload,
        "source_reported_maturing_position_count",
        "sourceReportedMaturingPositionCount",
        "maturing_position_count",
        "maturingPositionCount",
        "maturing_holding_count",
        "maturingHoldingCount",
    )
    if value is None:
        raise CoreSourceUnavailable(code="core_maturing_position_count_missing")
    if value < 0:
        raise CoreSourceUnavailable(code="core_maturing_position_count_malformed")
    return value


def _text_field(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _int_field(payload: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise CoreSourceUnavailable(code=f"core_{key}_malformed") from exc
    return None


def _min_projected_cumulative_cashflow(payload: dict[str, Any]) -> Decimal | None:
    values: list[Decimal] = []
    points = payload.get("points")
    if isinstance(points, list):
        for point in points:
            if not isinstance(point, dict):
                continue
            value = point.get("projected_cumulative_cashflow") or point.get(
                "projectedCumulativeCashflow"
            )
            if value is None:
                continue
            values.append(_decimal_value(value, code="core_cashflow_projection_malformed"))
    if values:
        return min(values)
    total = payload.get("total_net_cashflow") or payload.get("totalNetCashflow")
    if total is None:
        return None
    return _decimal_value(total, code="core_cashflow_projection_malformed")


def _decimal_value(value: object, *, code: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise CoreSourceUnavailable(code=code) from exc


def _low_income_cashflow_diagnostic(
    *,
    cash_movement_count: int | None,
    min_projected_cumulative_cashflow: Decimal | None,
) -> str:
    if cash_movement_count is None:
        return "core_cash_movement_count_missing"
    if min_projected_cumulative_cashflow is None:
        return "core_cashflow_projection_missing"
    return "core_cashflow_liquidity_evidence_ready"


def _assignment_effective_for_as_of_date(payload: dict[str, Any], as_of_date: date) -> bool:
    effective_from = _optional_date_field(payload, "effective_from", "effectiveFrom")
    effective_to = _optional_date_field(payload, "effective_to", "effectiveTo")
    if effective_from is None:
        return False
    if effective_from > as_of_date:
        return False
    return effective_to is None or effective_to >= as_of_date


def _benchmark_assignment_diagnostic(
    *,
    benchmark_identity_resolved: bool,
    assignment_effective_for_as_of_date: bool,
    assignment_status: str | None,
    assignment_version_present: bool,
) -> str:
    if not benchmark_identity_resolved:
        return "core_benchmark_assignment_benchmark_identity_missing"
    if not assignment_effective_for_as_of_date:
        return "core_benchmark_assignment_not_effective_for_as_of_date"
    if assignment_status is None:
        return "core_benchmark_assignment_status_missing"
    if assignment_status.lower() != "active":
        return f"core_benchmark_assignment_{assignment_status.lower()}"
    if not assignment_version_present:
        return "core_benchmark_assignment_version_missing"
    return "core_benchmark_assignment_ready"


def _content_hash(payload: dict[str, Any]) -> str:
    for key in (
        "source_batch_fingerprint",
        "sourceBatchFingerprint",
        "content_hash",
        "contentHash",
        "source_digest",
        "sourceDigest",
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
    return EvidenceFreshness.UNAVAILABLE
