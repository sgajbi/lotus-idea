from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import cast

from app.domain import EvidenceFreshness, SourceSystem
from app.domain.evidence_digest import is_sha256_digest
from app.ports.core_sources import (
    CoreCashMovementSummaryEvidence,
    CoreCashflowProjectionEvidence,
    CoreLowIncomeEvidence,
    CoreSourceProductRuntimeEvidence,
)

_MOVEMENT_PRODUCT_ID = "lotus-core:PortfolioCashMovementSummary:v1"
_MOVEMENT_PRODUCT_NAME = "PortfolioCashMovementSummary"
_PROJECTION_PRODUCT_ID = "lotus-core:PortfolioCashflowProjection:v1"
_PROJECTION_PRODUCT_NAME = "PortfolioCashflowProjection"
_PRODUCT_VERSION = "v1"
_COMPLETE = "COMPLETE"


def low_income_source_qualification_blockers(
    *,
    tenant_id: str,
    portfolio_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    horizon_days: int,
    correlation_id: str | None,
    evidence: CoreLowIncomeEvidence,
) -> tuple[str, ...]:
    blockers: list[str] = []
    _validate_source_ref(
        blockers,
        evidence.cash_movement_ref,
        product_id=_MOVEMENT_PRODUCT_ID,
        as_of_date=as_of_date,
        prefix="core_cash_movement",
    )
    _validate_source_ref(
        blockers,
        evidence.cashflow_projection_ref,
        product_id=_PROJECTION_PRODUCT_ID,
        as_of_date=as_of_date,
        prefix="core_cashflow_projection",
    )
    movement = evidence.cash_movement_product
    projection = evidence.cashflow_projection_product
    if movement is None:
        blockers.append("core_cash_movement_receipt_missing")
    else:
        blockers.extend(
            _movement_blockers(
                tenant_id=tenant_id,
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=correlation_id,
                product=movement,
                ref=evidence.cash_movement_ref,
            )
        )
    if projection is None:
        blockers.append("core_cashflow_projection_receipt_missing")
    else:
        blockers.extend(
            _projection_blockers(
                tenant_id=tenant_id,
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                horizon_days=horizon_days,
                correlation_id=correlation_id,
                product=projection,
                ref=evidence.cashflow_projection_ref,
            )
        )
    if not evidence.entitlement_allowed:
        blockers.append("core_cashflow_entitlement_denied")
    if evidence.cashflow_diagnostic != "core_cashflow_liquidity_evidence_ready":
        blockers.append("core_cashflow_diagnostic_not_ready")
    expected_min = minimum_projected_cashflow(projection)
    if evidence.source_reported_min_projected_cumulative_cashflow != expected_min:
        blockers.append("core_cashflow_minimum_mismatch")
    if evidence.cash_movement_count != (movement.cashflow_count if movement else None):
        blockers.append("core_cash_movement_count_mismatch")
    return tuple(dict.fromkeys(blockers))


def minimum_projected_cashflow(
    product: CoreCashflowProjectionEvidence | None,
) -> Decimal | None:
    if product is None or not product.points:
        return None
    values = [point.projected_cumulative_cashflow for point in product.points]
    if any(not isinstance(value, Decimal) for value in values):
        return None
    return min(value for value in values if isinstance(value, Decimal))


def _validate_source_ref(
    blockers: list[str],
    ref: object,
    *,
    product_id: str,
    as_of_date: date,
    prefix: str,
) -> None:
    if (
        ref is None
        or getattr(ref, "source_system", None) is not SourceSystem.LOTUS_CORE
        or getattr(ref, "product_id", None) != product_id
    ):
        blockers.append(f"{prefix}_source_ref_missing")
    elif getattr(ref, "as_of_date", None) != as_of_date:
        blockers.append(f"{prefix}_scope_mismatch")
    elif getattr(ref, "freshness", None) is not EvidenceFreshness.CURRENT:
        blockers.append(f"{prefix}_evidence_not_current")


def _movement_blockers(
    *,
    tenant_id: str,
    portfolio_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    correlation_id: str | None,
    product: CoreCashMovementSummaryEvidence,
    ref: object,
) -> tuple[str, ...]:
    blockers = _runtime_metadata_blockers(
        tenant_id=tenant_id,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        correlation_id=correlation_id,
        runtime=product.runtime,
        ref=ref,
        product_name=_MOVEMENT_PRODUCT_NAME,
        prefix="core_cash_movement",
    )
    if product.start_date != as_of_date or product.end_date != as_of_date:
        blockers.append("core_cash_movement_window_mismatch")
    counts = [bucket.cashflow_count for bucket in product.buckets]
    if (
        not isinstance(product.cashflow_count, int)
        or product.cashflow_count < 0
        or any(not isinstance(value, int) or value < 0 for value in counts)
        or sum(cast(list[int], counts)) != product.cashflow_count
    ):
        blockers.append("core_cash_movement_counts_invalid")
    keys: set[tuple[object, ...]] = set()
    for bucket in product.buckets:
        key = (
            bucket.classification,
            bucket.timing,
            bucket.currency,
            bucket.is_position_flow,
            bucket.is_portfolio_flow,
        )
        if key in keys or not all(isinstance(value, str) and value for value in key[:3]):
            blockers.append("core_cash_movement_buckets_invalid")
            break
        keys.add(key)
        if not _movement_direction_reconciles(bucket.total_amount, bucket.movement_direction):
            blockers.append("core_cash_movement_direction_mismatch")
            break
    return tuple(blockers)


def _projection_blockers(
    *,
    tenant_id: str,
    portfolio_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    horizon_days: int,
    correlation_id: str | None,
    product: CoreCashflowProjectionEvidence,
    ref: object,
) -> tuple[str, ...]:
    blockers = _runtime_metadata_blockers(
        tenant_id=tenant_id,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        correlation_id=correlation_id,
        runtime=product.runtime,
        ref=ref,
        product_name=_PROJECTION_PRODUCT_NAME,
        prefix="core_cashflow_projection",
    )
    if (
        product.range_start_date != as_of_date
        or product.range_end_date != as_of_date + timedelta(days=horizon_days)
        or product.include_projected is not True
        or product.projection_days != horizon_days
        or not isinstance(product.portfolio_currency, str)
        or not product.portfolio_currency.strip()
    ):
        blockers.append("core_cashflow_projection_scope_mismatch")
    if not _projection_series_reconciles(as_of_date, horizon_days, product):
        blockers.append("core_cashflow_projection_series_invalid")
    return tuple(blockers)


def _runtime_metadata_blockers(
    *,
    tenant_id: str,
    portfolio_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    correlation_id: str | None,
    runtime: CoreSourceProductRuntimeEvidence,
    ref: object,
    product_name: str,
    prefix: str,
) -> list[str]:
    blockers: list[str] = []
    if (
        runtime.product_name != product_name
        or runtime.product_version != _PRODUCT_VERSION
        or runtime.tenant_id != tenant_id
        or runtime.portfolio_id != portfolio_id
        or runtime.as_of_date != as_of_date
    ):
        blockers.append(f"{prefix}_response_scope_mismatch")
    if (
        runtime.generated_at_utc is None
        or runtime.generated_at_utc > evaluated_at_utc
        or runtime.latest_evidence_at_utc is None
        or runtime.latest_evidence_at_utc > runtime.generated_at_utc
    ):
        blockers.append(f"{prefix}_evidence_time_invalid")
    hashes = (
        getattr(ref, "content_hash", None),
        runtime.source_batch_fingerprint,
        runtime.content_hash,
        runtime.source_digest,
    )
    if not all(is_sha256_digest(value) for value in hashes) or len(set(hashes)) != 1:
        blockers.append(f"{prefix}_source_digest_mismatch")
    if (
        (runtime.reconciliation_status or "").upper() != _COMPLETE
        or (runtime.data_quality_status or "").upper() != _COMPLETE
        or runtime.degradation_status != "NONE"
        or runtime.degradation_reason_codes
        or runtime.degradation_detail_count != 0
        or not runtime.source_evidence_current
        or (runtime.freshness_status or "").upper() != "CURRENT"
    ):
        blockers.append(f"{prefix}_supportability_incomplete")
    if not runtime.restatement_version or not runtime.policy_version or not runtime.snapshot_id:
        blockers.append(f"{prefix}_governance_identity_missing")
    if correlation_id is None or runtime.correlation_id != correlation_id:
        blockers.append(f"{prefix}_correlation_binding_missing")
    return blockers


def _projection_series_reconciles(
    as_of_date: date,
    horizon_days: int,
    product: CoreCashflowProjectionEvidence,
) -> bool:
    if len(product.points) != horizon_days + 1:
        return False
    running = Decimal("0")
    booked_total = Decimal("0")
    projected_total = Decimal("0")
    for index, point in enumerate(product.points):
        values = (
            point.booked_net_cashflow,
            point.projected_settlement_cashflow,
            point.net_cashflow,
            point.projected_cumulative_cashflow,
        )
        if point.projection_date != as_of_date + timedelta(days=index) or any(
            not isinstance(value, Decimal) for value in values
        ):
            return False
        booked, projected, net, cumulative = cast(tuple[Decimal, Decimal, Decimal, Decimal], values)
        if booked + projected != net:
            return False
        running += net
        booked_total += booked
        projected_total += projected
        if cumulative != running:
            return False
    return (
        product.booked_total_net_cashflow == booked_total
        and product.projected_settlement_total_cashflow == projected_total
        and product.total_net_cashflow == running
    )


def _movement_direction_reconciles(amount: Decimal | None, direction: str | None) -> bool:
    if not isinstance(amount, Decimal):
        return False
    expected = "INFLOW" if amount > 0 else "OUTFLOW" if amount < 0 else "FLAT"
    return direction == expected
