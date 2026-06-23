from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.source_ingestion_live_proof import (
    LIVE_PROOF_SCHEMA_VERSION,
    build_source_ingestion_live_proof_payload,
    live_core_source_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    error: Exception | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        if self.error is not None:
            raise self.error
        return _core_evidence()


def test_live_proof_payload_remains_source_safe_and_not_promoted() -> None:
    payload = build_source_ingestion_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        worker_summary={
            "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
            "mode": "run_once",
            "sourceAuthority": "lotus-core",
            "durableStorageBacked": True,
            "totalCount": 1,
            "decisionCounts": {"accepted": 1, "replayed": 0},
        },
    )

    assert payload["schemaVersion"] == LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert "live_core_source_proof_missing" not in payload["proofBlockers"]
    assert "scheduled_worker_deploy_proof_missing" in payload["remainingCertificationBlockers"]
    assert live_core_source_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "idempotencyKey" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_live_proof_does_not_validate() -> None:
    payload = build_source_ingestion_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        worker_summary={
            "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
            "mode": "run_once",
            "status": "blocked",
            "sourceAuthority": "lotus-core",
            "durableStorageBacked": True,
            "totalCount": 0,
            "decisionCounts": {"accepted": 0, "replayed": 0},
            "errorCode": "core_source_unavailable",
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "live_core_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_core_source_unavailable" in payload["proofBlockers"]
    assert live_core_source_proof_is_valid(payload) is False


def test_live_proof_cli_writes_blocked_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )
    output_path = tmp_path / "source-ingestion-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda **_kwargs: RecordingCoreSource(
            error=CoreSourceUnavailable(code="core_source_unavailable")
        ),
    )

    result = module.main(
        [
            "--manifest",
            str(manifest_path),
            "--core-base-url",
            "http://localhost:8100",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "completed"
    assert payload["liveCoreSourceAttempted"] is True
    assert "no_candidate_ingestion_evidence" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "idempotencyKey" not in serialized


def test_live_proof_cli_accepts_split_core_source_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )
    output_path = tmp_path / "source-ingestion-live-proof.json"

    monkeypatch.setattr(
        module, "LotusCoreHighCashSourceAdapter", lambda **_kwargs: RecordingCoreSource()
    )

    result = module.main(
        [
            "--manifest",
            str(manifest_path),
            "--core-query-base-url",
            "http://localhost:8201",
            "--core-query-control-plane-base-url",
            "http://localhost:8202",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["liveCoreSourceAttempted"] is True
    assert payload["runStatus"] == "completed"
    assert "live_core_source_proof_missing" not in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=GENERATED_AT,
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


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_source_ingestion_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_source_ingestion_live_proof", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
