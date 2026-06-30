from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceEntitlementDenied,
    ManageSourceUnavailable,
)


PRODUCT_VERSION = "v1"
ACTION_REGISTER_PRODUCT_ID = "lotus-manage:PortfolioActionRegister:v1"
MANDATE_PERFORMANCE_HEALTH_PRODUCT_ID = "lotus-performance:MandatePerformanceHealthContext:v1"
MANDATE_RISK_HEALTH_PRODUCT_ID = "lotus-risk:MandateRiskHealthContext:v1"
ACTION_REGISTER_SUPPORTABILITY_ROUTE = "/api/v1/rebalance/supportability/summary"


@dataclass(frozen=True)
class _ActionRegisterPosture:
    workflow_decision_count: int
    lineage_edge_count: int
    supportability_state: str | None
    supportability_reason: str | None
    freshness_bucket: str | None
    portfolio_scope_confirmed: bool


class LotusManageMandateHealthSourceAdapter:
    def __init__(self, manage_client: DownstreamJsonClient) -> None:
        self._manage_client = manage_client

    def fetch_mandate_health_evidence(
        self, request: ManageMandateHealthEvidenceRequest
    ) -> ManageMandateHealthEvidence:
        try:
            payload = self._manage_client.get_json(
                ACTION_REGISTER_SUPPORTABILITY_ROUTE,
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise ManageSourceEntitlementDenied from exc
            raise ManageSourceUnavailable(code=exc.code) from exc

        posture = _action_register_posture(payload, request=request)
        return ManageMandateHealthEvidence(
            workflow_decision_count=posture.workflow_decision_count,
            lineage_edge_count=posture.lineage_edge_count,
            supportability_state=posture.supportability_state,
            supportability_reason=posture.supportability_reason,
            freshness_bucket=posture.freshness_bucket,
            portfolio_scope_confirmed=posture.portfolio_scope_confirmed,
            action_register_ref=_source_ref(payload, posture=posture, request=request),
            mandate_performance_health_ref=_source_product_ref(
                payload,
                supportability_product_key="mandate_performance_health_ref",
                camel_key="mandatePerformanceHealthRef",
                product_id=MANDATE_PERFORMANCE_HEALTH_PRODUCT_ID,
                source_system=SourceSystem.LOTUS_PERFORMANCE,
                default_route="/performance/mandate-health-context",
                request=request,
            ),
            mandate_risk_health_ref=_source_product_ref(
                payload,
                supportability_product_key="mandate_risk_health_ref",
                camel_key="mandateRiskHealthRef",
                product_id=MANDATE_RISK_HEALTH_PRODUCT_ID,
                source_system=SourceSystem.LOTUS_RISK,
                default_route="/analytics/risk/mandate-health-context",
                request=request,
            ),
            manage_diagnostic=_diagnostic(posture),
        )


def _action_register_posture(
    payload: dict[str, Any],
    *,
    request: ManageMandateHealthEvidenceRequest,
) -> _ActionRegisterPosture:
    supportability = _optional_object_field(payload, "supportability")
    return _ActionRegisterPosture(
        workflow_decision_count=_int_field(
            payload,
            "workflow_decision_count",
            code="manage_workflow_decision_count_malformed",
        ),
        lineage_edge_count=_int_field(
            payload,
            "lineage_edge_count",
            code="manage_lineage_edge_count_malformed",
        ),
        supportability_state=_text_field(supportability, "state"),
        supportability_reason=_text_field(supportability, "reason"),
        freshness_bucket=_text_field(supportability, "freshness_bucket"),
        portfolio_scope_confirmed=_portfolio_scope_confirmed(payload, request=request),
    )


def _source_ref(
    payload: dict[str, Any],
    *,
    posture: _ActionRegisterPosture,
    request: ManageMandateHealthEvidenceRequest,
) -> SourceRef:
    return SourceRef(
        product_id=ACTION_REGISTER_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_MANAGE,
        product_version=str(
            payload.get("product_version") or payload.get("productVersion") or PRODUCT_VERSION
        ),
        route=ACTION_REGISTER_SUPPORTABILITY_ROUTE,
        as_of_date=request.as_of_date,
        generated_at_utc=_generated_at(payload, fallback=request.evaluated_at_utc),
        content_hash=_content_hash(payload),
        data_quality_status=posture.supportability_state or "unknown",
        freshness=_freshness(posture),
    )


def _source_product_ref(
    payload: dict[str, Any],
    *,
    supportability_product_key: str,
    camel_key: str,
    product_id: str,
    source_system: SourceSystem,
    default_route: str,
    request: ManageMandateHealthEvidenceRequest,
) -> SourceRef | None:
    supportability = _optional_object_field(payload, "supportability")
    ref_payload = _source_ref_payload(
        payload,
        supportability=supportability,
        supportability_product_key=supportability_product_key,
        camel_key=camel_key,
        product_id=product_id,
    )
    if ref_payload is None:
        return None
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version=_text_field(ref_payload, "product_version")
        or _text_field(ref_payload, "productVersion")
        or PRODUCT_VERSION,
        route=_text_field(ref_payload, "route")
        or _text_field(ref_payload, "source_route")
        or _text_field(ref_payload, "sourceRoute")
        or default_route,
        as_of_date=request.as_of_date,
        generated_at_utc=_generated_at(ref_payload, fallback=request.evaluated_at_utc),
        content_hash=_content_hash(ref_payload),
        data_quality_status=_text_field(ref_payload, "data_quality_status")
        or _text_field(ref_payload, "dataQualityStatus")
        or _text_field(ref_payload, "health_state")
        or _text_field(ref_payload, "healthState")
        or "unknown",
        freshness=_freshness_from_ref_payload(ref_payload),
    )


def _source_ref_payload(
    payload: dict[str, Any],
    *,
    supportability: dict[str, Any],
    supportability_product_key: str,
    camel_key: str,
    product_id: str,
) -> dict[str, Any] | None:
    for container in (payload, supportability):
        for key in (supportability_product_key, camel_key):
            value = container.get(key)
            if isinstance(value, dict):
                return value
    for container in (payload, supportability):
        for key in ("source_refs", "sourceRefs"):
            value = container.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and _ref_product_id(item) == product_id:
                        return item
    return None


def _ref_product_id(payload: dict[str, Any]) -> str | None:
    for key in ("product_id", "productId", "source_product_id", "sourceProductId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _freshness_from_ref_payload(payload: dict[str, Any]) -> EvidenceFreshness:
    for key in ("freshness", "freshness_bucket", "freshnessBucket"):
        value = payload.get(key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"current", "same_day"}:
                return EvidenceFreshness.CURRENT
            if normalized == "stale":
                return EvidenceFreshness.STALE
            if normalized == "expired":
                return EvidenceFreshness.EXPIRED
            if normalized in {"unavailable", "missing"}:
                return EvidenceFreshness.UNAVAILABLE
    return EvidenceFreshness.UNAVAILABLE


def _optional_object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ManageSourceUnavailable(code=f"manage_{key}_malformed")


def _int_field(payload: dict[str, Any], key: str, *, code: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ManageSourceUnavailable(code=code)
    return value


def _text_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _portfolio_scope_confirmed(
    payload: dict[str, Any],
    *,
    request: ManageMandateHealthEvidenceRequest,
) -> bool:
    if payload.get("portfolio_scope_confirmed") is True:
        return True
    portfolio_id = payload.get("portfolio_id") or payload.get("portfolioId")
    if isinstance(portfolio_id, str) and portfolio_id == request.portfolio_id:
        return True
    supportability = _optional_object_field(payload, "supportability")
    supportability_portfolio_id = supportability.get("portfolio_id") or supportability.get(
        "portfolioId"
    )
    return isinstance(supportability_portfolio_id, str) and (
        supportability_portfolio_id == request.portfolio_id
    )


def _generated_at(payload: dict[str, Any], *, fallback: datetime) -> datetime:
    for key in (
        "generated_at",
        "generatedAt",
        "generated_at_utc",
        "generatedAtUtc",
        "newest_operation_created_at",
        "newest_run_created_at",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
    return fallback


def _content_hash(payload: dict[str, Any]) -> str:
    for key in (
        "content_hash",
        "contentHash",
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
    raise ManageSourceUnavailable(code="manage_content_hash_missing")


def _freshness(posture: _ActionRegisterPosture) -> EvidenceFreshness:
    freshness_bucket = (posture.freshness_bucket or "").lower()
    if freshness_bucket in {"current", "same_day"}:
        return EvidenceFreshness.CURRENT
    if freshness_bucket == "stale":
        return EvidenceFreshness.STALE
    if freshness_bucket == "expired":
        return EvidenceFreshness.EXPIRED
    return EvidenceFreshness.UNAVAILABLE


def _diagnostic(posture: _ActionRegisterPosture) -> str:
    state = posture.supportability_state or "unknown"
    scope = "portfolio_scope" if posture.portfolio_scope_confirmed else "store_wide_scope"
    return f"manage_action_register_{state.lower()}_{scope}"
