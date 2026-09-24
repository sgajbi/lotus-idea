from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.application.low_income_cashflow_runtime_evidence import (
    EvaluateLowIncomeCashflowReadiness,
    build_low_income_cashflow_runtime_execution,
    evaluate_low_income_cashflow_readiness,
)
from app.domain import (
    EvidenceFreshness,
    SourceReconciliationPosture,
    SourceRef,
    SourceRevisionClaims,
    SourceSystem,
)
from app.domain.persistence import InMemoryIdeaRepository
from app.ports.core_sources import (
    CoreCashMovementBucketEvidence,
    CoreCashMovementSummaryEvidence,
    CoreCashflowProjectionEvidence,
    CoreCashflowProjectionPointEvidence,
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreSourceProductRuntimeEvidence,
)

MOVEMENT_HASH = "sha256:" + "c" * 64
PROJECTION_HASH = "sha256:" + "d" * 64


class AuthoritativeCoreLowIncomeSource:
    def __init__(self, *, minimum_cashflow: Decimal = Decimal("-12500")) -> None:
        self.minimum_cashflow = minimum_cashflow

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        return authoritative_low_income_evidence(
            request=request,
            minimum_cashflow=self.minimum_cashflow,
        )

    def close(self) -> None:
        return None


def authoritative_low_income_evidence(
    *,
    request: CoreLowIncomeEvidenceRequest,
    minimum_cashflow: Decimal = Decimal("-12500"),
    movement_hash: str = MOVEMENT_HASH,
    projection_hash: str = PROJECTION_HASH,
    source_revision: str = "1",
    source_cut_id: str = "cashflow-cut-1",
) -> CoreLowIncomeEvidence:
    generated_at = request.evaluated_at_utc - timedelta(minutes=1)
    movement_ref = _source_ref(
        product_id="lotus-core:PortfolioCashMovementSummary:v1",
        route="/portfolios/{portfolio_id}/cash-movement-summary",
        content_hash=movement_hash,
        request=request,
        generated_at=generated_at,
        source_revision=source_revision,
        source_cut_id=source_cut_id,
    )
    projection_ref = _source_ref(
        product_id="lotus-core:PortfolioCashflowProjection:v1",
        route="/portfolios/{portfolio_id}/cashflow-projection",
        content_hash=projection_hash,
        request=request,
        generated_at=generated_at,
        source_revision=source_revision,
        source_cut_id=source_cut_id,
    )
    movement_count = 0 if minimum_cashflow == 0 else 1
    movement = CoreCashMovementSummaryEvidence(
        runtime=_runtime(
            request=request,
            generated_at=generated_at,
            product_name="PortfolioCashMovementSummary",
            content_hash=movement_hash,
            source_revision=source_revision,
        ),
        start_date=request.as_of_date,
        end_date=request.as_of_date,
        buckets=(
            (
                CoreCashMovementBucketEvidence(
                    classification="CASHFLOW_OUT",
                    timing="SETTLED",
                    currency="USD",
                    is_position_flow=False,
                    is_portfolio_flow=True,
                    cashflow_count=1,
                    total_amount=minimum_cashflow,
                    movement_direction="OUTFLOW",
                ),
            )
            if movement_count
            else ()
        ),
        cashflow_count=movement_count,
    )
    points: list[CoreCashflowProjectionPointEvidence] = []
    running = Decimal("0")
    for index in range(request.horizon_days + 1):
        projected = minimum_cashflow if index == 0 else Decimal("0")
        running += projected
        points.append(
            CoreCashflowProjectionPointEvidence(
                projection_date=request.as_of_date + timedelta(days=index),
                booked_net_cashflow=Decimal("0"),
                projected_settlement_cashflow=projected,
                net_cashflow=projected,
                projected_cumulative_cashflow=running,
            )
        )
    projection = CoreCashflowProjectionEvidence(
        runtime=_runtime(
            request=request,
            generated_at=generated_at,
            product_name="PortfolioCashflowProjection",
            content_hash=projection_hash,
            source_revision=source_revision,
        ),
        range_start_date=request.as_of_date,
        range_end_date=request.as_of_date + timedelta(days=request.horizon_days),
        include_projected=True,
        portfolio_currency="USD",
        points=tuple(points),
        total_net_cashflow=minimum_cashflow,
        booked_total_net_cashflow=Decimal("0"),
        projected_settlement_total_cashflow=minimum_cashflow,
        projection_days=request.horizon_days,
    )
    return CoreLowIncomeEvidence(
        source_reported_min_projected_cumulative_cashflow=minimum_cashflow,
        cash_movement_count=movement_count,
        cash_movement_ref=movement_ref,
        cashflow_projection_ref=projection_ref,
        cashflow_diagnostic="core_cashflow_liquidity_evidence_ready",
        cash_movement_product=movement,
        cashflow_projection_product=projection,
    )


def valid_low_income_cashflow_runtime_evidence(
    *,
    evaluated_at_utc: datetime,
    as_of_date: date | None = None,
    minimum_cashflow: Decimal = Decimal("-12500"),
) -> dict[str, Any]:
    command = EvaluateLowIncomeCashflowReadiness(
        tenant_id="test-tenant",
        book_id="test-book",
        portfolio_id="test-portfolio",
        client_id="test-client",
        as_of_date=as_of_date or evaluated_at_utc.date(),
        evaluated_at_utc=evaluated_at_utc,
        accepted_at_utc=evaluated_at_utc,
        idempotency_key="test-low-income-runtime",
        actor_subject="test-runtime-proof",
        horizon_days=30,
        correlation_id="corr-test",
        trace_id="trace-test",
    )
    result = evaluate_low_income_cashflow_readiness(
        command,
        core_source=AuthoritativeCoreLowIncomeSource(minimum_cashflow=minimum_cashflow),
        repository=InMemoryIdeaRepository(),
    )
    return build_low_income_cashflow_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
        durable_storage_backed=True,
    )


def _runtime(
    *,
    request: CoreLowIncomeEvidenceRequest,
    generated_at: datetime,
    product_name: str,
    content_hash: str,
    source_revision: str,
) -> CoreSourceProductRuntimeEvidence:
    return CoreSourceProductRuntimeEvidence(
        product_name=product_name,
        product_version="v1",
        tenant_id=request.tenant_id,
        portfolio_id=request.portfolio_id,
        generated_at_utc=generated_at,
        as_of_date=request.as_of_date,
        restatement_version="restatement-v1",
        reconciliation_status="COMPLETE",
        data_quality_status="COMPLETE",
        latest_evidence_at_utc=generated_at - timedelta(minutes=1),
        source_batch_fingerprint=content_hash,
        snapshot_id=f"{product_name.lower()}-snapshot-{source_revision}",
        content_hash=content_hash,
        source_digest=content_hash,
        source_refs=(f"lotus-core://source/{product_name}/{source_revision}",),
        source_lineage=(("source_owner", "lotus-core"),),
        degradation_status="NONE",
        degradation_reason_codes=(),
        degradation_detail_count=0,
        source_evidence_current=True,
        freshness_status="CURRENT",
        policy_version="cashflow-policy-v1",
        correlation_id=request.correlation_id,
    )


def _source_ref(
    *,
    product_id: str,
    route: str,
    content_hash: str,
    request: CoreLowIncomeEvidenceRequest,
    generated_at: datetime,
    source_revision: str,
    source_cut_id: str,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route,
        as_of_date=request.as_of_date,
        generated_at_utc=generated_at,
        content_hash=content_hash,
        data_quality_status="COMPLETE",
        freshness=EvidenceFreshness.CURRENT,
        revision_claims=SourceRevisionClaims(
            snapshot_id=f"{product_id}:snapshot-{source_revision}",
            source_revision=source_revision,
            restatement_version="restatement-v1",
            source_cut_id=source_cut_id,
            reconciliation_posture=SourceReconciliationPosture.COMPLETE,
        ),
    )
