from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION,
    build_low_income_core_cashflow_live_proof_payload,
    low_income_core_cashflow_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingCoreSource:
    error: Exception | None = None

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        if self.error is not None:
            raise self.error
        return _low_income_evidence()


def test_low_income_core_cashflow_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "cashMovementRefPresent": True,
            "cashflowProjectionRefPresent": True,
            "cashMovementCountPresent": True,
            "projectedCumulativeCashflowPresent": True,
            "sourceEvidenceCurrent": True,
            "cashflowDiagnostic": "core_cashflow_liquidity_evidence_ready",
            "sourceDiagnosticCodes": ["core_cashflow_liquidity_evidence_ready"],
        },
    )

    assert payload["schemaVersion"] == LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["cashMovementRefPresent"] is True
    assert payload["cashflowProjectionRefPresent"] is True
    assert payload["cashMovementCountPresent"] is True
    assert payload["projectedCumulativeCashflowPresent"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_live_core_cashflow_source_proof_missing"
    ]
    assert (
        "opportunity_archetype_workbench_product_proof_missing"
        in (payload["remainingCertificationBlockers"])
    )
    assert (
        "opportunity_archetype_client_publication_not_ready"
        in (payload["remainingCertificationBlockers"])
    )
    assert low_income_core_cashflow_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_blocked_low_income_core_cashflow_live_proof_does_not_validate() -> None:
    payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "errorCode": "core_cashflow_source_unavailable",
            "cashMovementRefPresent": False,
            "cashflowProjectionRefPresent": False,
            "cashMovementCountPresent": False,
            "projectedCumulativeCashflowPresent": False,
            "sourceEvidenceCurrent": False,
            "cashflowDiagnostic": "core_cashflow_source_unavailable",
            "sourceDiagnosticCodes": ["core_cashflow_source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "core_cashflow_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_core_cashflow_source_unavailable" in payload["proofBlockers"]
    assert "core_cash_movement_source_ref_missing" in payload["proofBlockers"]
    assert "core_cashflow_projection_source_ref_missing" in payload["proofBlockers"]
    assert "core_projected_cumulative_cashflow_missing" in payload["proofBlockers"]
    assert "core_cashflow_liquidity_evidence_not_ready" in payload["proofBlockers"]
    assert low_income_core_cashflow_live_proof_is_valid(payload) is False


def test_low_income_core_cashflow_live_proof_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_low_income_core_cashflow_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            live_core_source_attempted=True,
            evidence_summary={},
        )


def test_low_income_core_cashflow_live_proof_rejects_stale_source_evidence() -> None:
    payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "cashMovementRefPresent": True,
            "cashflowProjectionRefPresent": True,
            "cashMovementCountPresent": True,
            "projectedCumulativeCashflowPresent": True,
            "sourceEvidenceCurrent": False,
            "cashflowDiagnostic": "core_cashflow_liquidity_evidence_ready",
            "sourceDiagnosticCodes": ["core_cashflow_stale"],
        },
    )

    assert "core_cashflow_evidence_not_current" in payload["proofBlockers"]
    assert low_income_core_cashflow_live_proof_is_valid(payload) is False


def test_low_income_core_cashflow_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=False,
        evidence_summary={
            "cashMovementRefPresent": True,
            "cashflowProjectionRefPresent": True,
            "cashMovementCountPresent": True,
            "projectedCumulativeCashflowPresent": True,
            "sourceEvidenceCurrent": True,
            "cashflowDiagnostic": "core_cashflow_liquidity_evidence_ready",
            "sourceDiagnosticCodes": "not-a-list",
        },
    )

    assert payload["runStatus"] == "completed"
    assert payload["sourceDiagnosticCodes"] == []
    assert "core_cashflow_source_proof_missing" in payload["proofBlockers"]
    assert low_income_core_cashflow_live_proof_is_valid(payload) is False


def test_low_income_core_cashflow_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "low-income-core-cashflow-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(),
    )

    result = module.main(
        [
            "--core-query-base-url",
            "http://localhost:8100",
            "--tenant-id",
            "default",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--horizon-days",
            "30",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--correlation-id",
            "corr-123",
            "--trace-id",
            "trace-123",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "completed"
    assert payload["liveCoreSourceAttempted"] is True
    assert payload["cashMovementRefPresent"] is True
    assert payload["cashflowProjectionRefPresent"] is True
    assert payload["cashflowDiagnostic"] == "core_cashflow_liquidity_evidence_ready"
    assert (
        "opportunity_archetype_live_core_cashflow_source_proof_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_low_income_core_cashflow_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "low-income-core-cashflow-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(
            error=CoreSourceUnavailable(code="core_cashflow_source_unavailable")
        ),
    )

    result = module.main(
        [
            "--core-query-base-url",
            "http://localhost:8100",
            "--tenant-id",
            "default",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 3
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "blocked"
    assert "source_error_core_cashflow_source_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _low_income_evidence() -> CoreLowIncomeEvidence:
    return CoreLowIncomeEvidence(
        source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
        cash_movement_count=4,
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        cashflow_diagnostic="core_cashflow_liquidity_evidence_ready",
    )


def _source_ref(product_id: str) -> SourceRef:
    route = (
        "/portfolios/{portfolio_id}/cash-movement-summary"
        if product_id.endswith("PortfolioCashMovementSummary:v1")
        else "/portfolios/{portfolio_id}/cashflow-projection"
    )
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route,
        as_of_date=AS_OF_DATE,
        generated_at_utc=GENERATED_AT,
        content_hash=f"sha256:{product_id.rsplit(':', 1)[0].lower()}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_low_income_core_cashflow_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_low_income_core_cashflow_live_proof", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
