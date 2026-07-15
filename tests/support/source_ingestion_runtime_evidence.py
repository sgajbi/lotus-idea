from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.source_ingestion import (
    HighCashSourceIngestionBatchResult,
    run_high_cash_source_ingestion_batch,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    SourceIngestionWorkerPlan,
    source_ingestion_worker_plan_from_manifest,
)
from app.application.source_ingestion_runtime_evidence import (
    build_source_ingestion_runtime_execution,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.core_sources import (
    CASHFLOW_PROJECTION_PRODUCT_ID,
    CASH_MOVEMENT_PRODUCT_ID,
    HOLDINGS_PRODUCT_ID,
    PORTFOLIO_STATE_PRODUCT_ID,
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass(frozen=True)
class FixedCoreHighCashSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        return self.evidence


def runtime_plan(*, work_item_count: int = 1) -> SourceIngestionWorkerPlan:
    return source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": EVALUATED_AT.isoformat(),
            "tenantId": "tenant-runtime-proof",
            "workItems": [
                {
                    "portfolioId": "PB_SG_GLOBAL_BAL_001",
                    "asOfDate": AS_OF_DATE.isoformat(),
                }
                for _ in range(work_item_count)
            ],
        }
    )


def runtime_result(
    plan: SourceIngestionWorkerPlan,
    *,
    repository: InMemoryIdeaRepository | None = None,
    evidence: CoreHighCashEvidence | None = None,
) -> HighCashSourceIngestionBatchResult:
    return run_high_cash_source_ingestion_batch(
        plan.command,
        core_source=FixedCoreHighCashSource(evidence or core_high_cash_evidence()),
        repository=repository or InMemoryIdeaRepository(),
    )


def runtime_execution(
    *,
    generated_at_utc: datetime = GENERATED_AT,
    durable_storage_backed: bool = True,
    work_item_count: int = 1,
) -> dict[str, Any]:
    plan = runtime_plan(work_item_count=work_item_count)
    return build_source_ingestion_runtime_execution(
        generated_at_utc=generated_at_utc,
        plan=plan,
        result=runtime_result(plan),
        durable_storage_backed=durable_storage_backed,
    )


def core_high_cash_evidence(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    as_of_date: date = AS_OF_DATE,
) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref(
            PORTFOLIO_STATE_PRODUCT_ID, freshness=freshness, as_of_date=as_of_date
        ),
        holdings_ref=_source_ref(HOLDINGS_PRODUCT_ID, freshness=freshness, as_of_date=as_of_date),
        cash_movement_ref=_source_ref(
            CASH_MOVEMENT_PRODUCT_ID, freshness=freshness, as_of_date=as_of_date
        ),
        cashflow_projection_ref=_source_ref(
            CASHFLOW_PROJECTION_PRODUCT_ID, freshness=freshness, as_of_date=as_of_date
        ),
        cash_weight_diagnostic="core_cash_weight_supported",
    )


def _source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness,
    as_of_date: date,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=as_of_date,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )
