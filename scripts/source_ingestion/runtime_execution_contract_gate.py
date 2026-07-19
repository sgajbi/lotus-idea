# ruff: noqa: E402
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_runtime_evidence import (
    SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_source_ingestion_runtime_execution,
    build_source_ingestion_runtime_execution,
    source_ingestion_runtime_execution_is_valid,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
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

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from proof_source_safety import (  # noqa: E402
    forbidden_content_validator,
    validate_forbidden_content,
)


GENERATOR = ROOT / "scripts" / "source_ingestion" / "generate_runtime_execution.py"
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
AS_OF_DATE = date(2026, 6, 21)

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "tenantId",
    "traceId",
    "transactionId",
}
FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
    "signal-ingestion:high-cash:lotus-core",
    "tenant-runtime-contract",
}

_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


@dataclass(frozen=True)
class _ContractCoreSource(CoreOpportunitySourcePort):
    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        return CoreHighCashEvidence(
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=_source_ref(PORTFOLIO_STATE_PRODUCT_ID),
            holdings_ref=_source_ref(HOLDINGS_PRODUCT_ID),
            cash_movement_ref=_source_ref(CASH_MOVEMENT_PRODUCT_ID),
            cashflow_projection_ref=_source_ref(CASHFLOW_PROJECTION_PRODUCT_ID),
            cash_weight_diagnostic="core_cash_weight_supported",
        )


def validate_source_ingestion_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.is_file():
        return ["scripts/source_ingestion/generate_runtime_execution.py is required"]

    plan = _plan()
    result = run_high_cash_source_ingestion_batch(
        plan.command,
        core_source=_ContractCoreSource(),
        repository=InMemoryIdeaRepository(),
    )
    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=result,
        durable_storage_backed=True,
    )
    if payload.get("schemaVersion") != SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION}")
    if payload.get("evidenceClass") != "runtime_execution":
        errors.append("source ingestion proof must declare runtime_execution evidence")
    if payload.get("aggregateBlockersSatisfied") != [
        "opportunity_archetype_live_core_source_proof_missing"
    ]:
        errors.append("runtime execution may clear only the live Core source blocker")
    if not source_ingestion_runtime_execution_is_valid(payload):
        errors.append("receipt-bound runtime execution fixture must validate")

    blocked = build_blocked_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        error_code="core_source_unavailable",
        durable_storage_backed=True,
    )
    if source_ingestion_runtime_execution_is_valid(blocked):
        errors.append("blocked source execution must not validate")

    forged = dict(payload)
    forged["liveCoreSourceAttempted"] = True
    if source_ingestion_runtime_execution_is_valid(forged):
        errors.append("legacy self-asserted live-source booleans must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _plan():
    return source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": EVALUATED_AT.isoformat(),
            "tenantId": "tenant-runtime-contract",
            "workItems": [
                {
                    "portfolioId": "PB_SG_GLOBAL_BAL_001",
                    "asOfDate": AS_OF_DATE.isoformat(),
                }
            ],
        }
    )


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def main() -> int:
    errors = validate_source_ingestion_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Source ingestion runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
