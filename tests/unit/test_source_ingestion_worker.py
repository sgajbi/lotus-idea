from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType
from typing import Any

import pytest

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
    summarize_source_ingestion_worker_failure,
    summarize_source_ingestion_worker_run,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    seen_request: CoreHighCashEvidenceRequest | None = None
    error: Exception | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
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
    check_summary = plan.check_summary()
    assert check_summary["mode"] == "check_only"
    assert check_summary["workItems"][0]["itemIndex"] == 0
    assert "portfolioId" not in check_summary["workItems"][0]


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


@pytest.mark.parametrize(
    ("manifest_update", "expected_error"),
    [
        ({"workItems": "not-a-list"}, "workItems must be a non-empty list"),
        ({"workItems": ["not-an-object"]}, "workItems[0] must be an object"),
        (
            {"workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21", "extra": "x"}]},
            "workItems[0] contains unsupported keys: extra",
        ),
        ({"actorSubject": " "}, "optional text fields must be non-empty strings when supplied"),
        ({"evaluatedAtUtc": "2026-06-21T10:00:00"}, "evaluatedAtUtc must be timezone-aware"),
        ({"maxItems": 0}, "maxItems must be a positive integer"),
    ],
)
def test_rejects_malformed_worker_manifest_fields(
    manifest_update: dict[str, object],
    expected_error: str,
) -> None:
    manifest: dict[str, object] = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21"}],
    }
    manifest.update(manifest_update)

    with pytest.raises(ValueError, match=re.escape(expected_error)):
        source_ingestion_worker_plan_from_manifest(manifest)


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
    assert summary["items"][0]["hasIdempotencyKey"] is True
    assert "idempotencyKey" not in summary["items"][0]
    assert "portfolioId" not in summary["items"][0]
    assert source.seen_request is not None
    assert source.seen_request.correlation_id == "corr-worker"
    assert source.seen_request.trace_id == "trace-worker"


def test_summarizes_worker_source_failure_without_source_payloads() -> None:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "workItems": [
                {
                    "portfolioId": PORTFOLIO_ID,
                    "asOfDate": "2026-06-21",
                    "idempotencyKey": "signal-ingestion:high-cash:lotus-core:explicit",
                }
            ],
        }
    )

    summary = summarize_source_ingestion_worker_failure(
        plan=plan,
        error_code="core_source_entitlement_denied",
        durable_storage_backed=False,
    )

    assert summary["mode"] == "run_once"
    assert summary["status"] == "blocked"
    assert summary["sourceAuthority"] == "lotus-core"
    assert summary["supportedFeaturePromoted"] is False
    assert summary["workItemCount"] == 1
    assert summary["errorCode"] == "core_source_entitlement_denied"
    assert summary["decisionCounts"]["accepted"] == 0
    assert "workItems" not in summary
    assert "portfolioId" not in json.dumps(summary)
    assert "idempotencyKey" not in json.dumps(summary)


def test_summarizes_worker_failure_with_default_safe_error_code() -> None:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "workItems": [{"portfolioId": PORTFOLIO_ID, "asOfDate": "2026-06-21"}],
        }
    )

    summary = summarize_source_ingestion_worker_failure(
        plan=plan,
        error_code=" ",
        durable_storage_backed=False,
    )

    assert summary["errorCode"] == "core_source_unavailable"
    assert summary["decisionCounts"]["blocked"] == 0


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
    assert payload["workItems"][0]["itemIndex"] == 0
    assert "portfolioId" not in captured.out


def test_cli_run_mode_returns_source_safe_item_block_for_core_entitlement_denial(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_worker_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(error=CoreSourceEntitlementDenied()),
    )

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--core-base-url",
                "http://localhost:8100",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["mode"] == "run_once"
    assert payload["decisionCounts"]["blocked"] == 1
    assert payload["items"][0]["decision"] == "blocked"
    assert payload["items"][0]["hasIdempotencyKey"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert "idempotencyKey" not in payload["items"][0]
    assert "signal-ingestion:high-cash:lotus-core" not in captured.out
    assert "portfolioId" not in captured.out


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
