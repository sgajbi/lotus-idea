from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.bond_maturity_live_proof import (
    BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION,
    bond_maturity_live_proof_is_valid,
    build_bond_maturity_live_proof_payload,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingCoreSource:
    error: Exception | None = None

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        if self.error is not None:
            raise self.error
        return _bond_maturity_evidence()


def test_bond_maturity_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary=_valid_summary(),
    )

    assert payload["schemaVersion"] == BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["holdingsRefPresent"] is True
    assert payload["maturityFactRefPresent"] is True
    assert payload["nextMaturityDatePresent"] is True
    assert payload["maturingPositionCountPresent"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_maturity_live_core_source_proof_missing"
    ]
    assert (
        "opportunity_archetype_workbench_product_proof_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert bond_maturity_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_blocked_bond_maturity_live_proof_does_not_validate() -> None:
    payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "errorCode": "core_maturity_source_unavailable",
            "holdingsRefPresent": False,
            "maturityFactRefPresent": False,
            "nextMaturityDatePresent": False,
            "maturingPositionCountPresent": False,
            "sourceEvidenceCurrent": False,
            "maturityDiagnostic": "core_maturity_source_unavailable",
            "sourceDiagnosticCodes": ["core_maturity_source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "core_maturity_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_core_maturity_source_unavailable" in payload["proofBlockers"]
    assert "core_holdings_source_ref_missing" in payload["proofBlockers"]
    assert "core_maturity_fact_source_ref_missing" in payload["proofBlockers"]
    assert "core_next_maturity_date_missing" in payload["proofBlockers"]
    assert "core_maturity_evidence_not_ready" in payload["proofBlockers"]
    assert bond_maturity_live_proof_is_valid(payload) is False


def test_bond_maturity_live_proof_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_bond_maturity_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            live_core_source_attempted=True,
            evidence_summary={},
        )


def test_bond_maturity_live_proof_rejects_stale_source_evidence() -> None:
    summary = _valid_summary()
    summary["sourceEvidenceCurrent"] = False
    summary["sourceDiagnosticCodes"] = ["core_maturity_stale"]
    payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary=summary,
    )

    assert "core_maturity_evidence_not_current" in payload["proofBlockers"]
    assert bond_maturity_live_proof_is_valid(payload) is False


def test_bond_maturity_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=False,
        evidence_summary={**_valid_summary(), "sourceDiagnosticCodes": "not-a-list"},
    )

    assert payload["sourceDiagnosticCodes"] == []
    assert "core_maturity_source_proof_missing" in payload["proofBlockers"]
    assert bond_maturity_live_proof_is_valid(payload) is False


def test_bond_maturity_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "bond-maturity-live-proof.json"

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
            "--maturity-window-days",
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
    assert payload["maturityDiagnostic"] == "core_maturity_evidence_ready"
    assert (
        "opportunity_archetype_maturity_live_core_source_proof_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_bond_maturity_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "bond-maturity-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(
            error=CoreSourceUnavailable(code="core_maturity_source_unavailable")
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
    assert "source_error_core_maturity_source_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _valid_summary() -> dict[str, object]:
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-core",
        "holdingsRefPresent": True,
        "maturityFactRefPresent": True,
        "nextMaturityDatePresent": True,
        "maturingPositionCountPresent": True,
        "sourceEvidenceCurrent": True,
        "maturityDiagnostic": "core_maturity_evidence_ready",
        "sourceDiagnosticCodes": ["core_maturity_evidence_ready"],
    }


def _bond_maturity_evidence() -> CoreBondMaturityEvidence:
    return CoreBondMaturityEvidence(
        source_reported_next_maturity_date=date(2026, 7, 10),
        source_reported_maturing_position_count=2,
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
        maturity_diagnostic="core_maturity_evidence_ready",
    )


def _source_ref(product_id: str) -> SourceRef:
    route_by_product = {
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/positions",
        "lotus-core:PortfolioMaturitySummary:v1": "/portfolios/{portfolio_id}/maturity-summary",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=GENERATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_bond_maturity_live_proof.py"
    spec = importlib.util.spec_from_file_location("generate_bond_maturity_live_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
