from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
    summarize_source_ingestion_worker_run,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    seen_request: CoreHighCashEvidenceRequest | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        return _core_evidence()


def test_loads_worker_manifest_as_bounded_batch_command() -> None:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "actorSubject": "signal-ingestion-worker",
            "maxItems": 10,
            "correlationId": "corr-worker",
            "traceId": "trace-worker",
            "workItems": [
                {
                    "portfolioId": PORTFOLIO_ID,
                    "asOfDate": "2026-06-21",
                    "idempotencyKey": "signal-ingestion:high-cash:lotus-core:explicit",
                }
            ],
        }
    )

    assert plan.schema_version == MANIFEST_SCHEMA_VERSION
    assert plan.command.evaluated_at_utc == EVALUATED_AT
    assert plan.command.max_items == 10
    assert plan.command.correlation_id == "corr-worker"
    assert plan.command.trace_id == "trace-worker"
    assert plan.command.work_items[0].portfolio_id == PORTFOLIO_ID
    assert plan.command.work_items[0].as_of_date == AS_OF_DATE
    assert plan.command.work_items[0].idempotency_key is not None
    assert plan.check_summary()["mode"] == "check_only"


def test_rejects_unknown_manifest_keys_before_worker_execution() -> None:
    invalid_manifest = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21"}],
        "unexpected": "value",
    }

    try:
        source_ingestion_worker_plan_from_manifest(invalid_manifest)
    except ValueError as exc:
        assert str(exc) == "manifest contains unsupported keys: unexpected"
    else:
        raise AssertionError("expected unknown manifest key to be rejected")


def test_rejects_unsupported_schema_version() -> None:
    invalid_manifest = {
        "schemaVersion": "lotus-idea.source-ingestion.high-cash.v0",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21"}],
    }

    try:
        source_ingestion_worker_plan_from_manifest(invalid_manifest)
    except ValueError as exc:
        assert str(exc) == f"schemaVersion must be {MANIFEST_SCHEMA_VERSION}"
    else:
        raise AssertionError("expected unsupported schema version to be rejected")


def test_summarizes_worker_run_without_source_payloads_or_supported_claims() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource()
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "correlationId": "corr-worker",
            "traceId": "trace-worker",
            "workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21"}],
        }
    )

    result = run_high_cash_source_ingestion_batch(
        plan.command,
        core_source=source,
        repository=repository,
    )
    summary = summarize_source_ingestion_worker_run(
        plan=plan,
        result=result,
        durable_storage_backed=False,
    )

    assert summary["mode"] == "run_once"
    assert summary["sourceAuthority"] == "lotus-core"
    assert summary["durableStorageBacked"] is False
    assert summary["supportedFeaturePromoted"] is False
    assert summary["decisionCounts"]["accepted"] == 1
    persistence = result.item_results[0].signal_result.persistence
    assert persistence is not None
    assert persistence.record is not None
    assert summary["items"][0]["candidateId"] == persistence.record.candidate.candidate_id
    assert str(summary["items"][0]["candidateId"]).startswith("idea_high_cash_")
    assert "portfolioId" not in summary["items"][0]
    assert source.seen_request is not None
    assert source.seen_request.correlation_id == "corr-worker"
    assert source.seen_request.trace_id == "trace-worker"


def test_cli_check_only_validates_example_manifest(capsys: Any) -> None:
    module = _load_worker_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )

    assert module.main(["--manifest", str(manifest_path), "--check-only"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schemaVersion"] == MANIFEST_SCHEMA_VERSION
    assert payload["mode"] == "check_only"
    assert payload["workItemCount"] == 1


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


def _core_evidence() -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def _load_worker_script() -> ModuleType:
    script_path = ROOT / "scripts" / "run_source_ingestion_worker.py"
    spec = importlib.util.spec_from_file_location("run_source_ingestion_worker", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
