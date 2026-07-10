from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.core_portfolio_state_live_proof import (
    CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION,
    build_core_portfolio_state_live_proof_payload,
    core_portfolio_state_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
    CoreSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingCoreSource:
    error: Exception | None = None

    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        if self.error is not None:
            raise self.error
        return _portfolio_state_evidence()


def test_core_portfolio_state_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
            "portfolioStateRefPresent": True,
            "sourceEvidenceCurrent": True,
            "sourceEvidenceAvailable": True,
            "sourceDiagnosticCodes": ["core_portfolio_state_ready"],
        },
    )

    assert payload["schemaVersion"] == CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["portfolioStateRefPresent"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["sourceEvidenceAvailable"] is True
    assert payload["rebalanceExecutionAuthorityGranted"] is False
    assert payload["orderExecutionReady"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_core_portfolio_state_source_ref_missing"
    ]
    assert (
        "opportunity_archetype_portfolio_scoped_manage_source_proof_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert (
        "opportunity_archetype_mandate_performance_health_source_ref_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert (
        "opportunity_archetype_mandate_risk_health_source_ref_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert (
        "opportunity_archetype_data_mesh_not_certified"
        in (payload["remainingCertificationBlockers"])
    )
    assert core_portfolio_state_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_blocked_core_portfolio_state_live_proof_does_not_validate() -> None:
    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
            "errorCode": "core_portfolio_state_source_unavailable",
            "portfolioStateRefPresent": False,
            "sourceEvidenceCurrent": False,
            "sourceEvidenceAvailable": False,
            "sourceDiagnosticCodes": ["core_portfolio_state_source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "core_portfolio_state_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_core_portfolio_state_source_unavailable" in payload["proofBlockers"]
    assert "core_portfolio_state_source_ref_missing" in payload["proofBlockers"]
    assert "core_portfolio_state_evidence_unavailable" in payload["proofBlockers"]
    assert "core_portfolio_state_evidence_not_current" in payload["proofBlockers"]
    assert core_portfolio_state_live_proof_is_valid(payload) is False


def test_core_portfolio_state_live_proof_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_core_portfolio_state_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            live_core_source_attempted=True,
            evidence_summary={},
        )


def test_core_portfolio_state_live_proof_rejects_stale_source_evidence() -> None:
    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
            "portfolioStateRefPresent": True,
            "sourceEvidenceCurrent": False,
            "sourceEvidenceAvailable": True,
            "sourceDiagnosticCodes": ["core_portfolio_state_stale"],
        },
    )

    assert "core_portfolio_state_evidence_not_current" in payload["proofBlockers"]
    assert core_portfolio_state_live_proof_is_valid(payload) is False


def test_core_portfolio_state_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=False,
        evidence_summary={
            "portfolioStateRefPresent": True,
            "sourceEvidenceCurrent": True,
            "sourceEvidenceAvailable": True,
            "sourceDiagnosticCodes": "not-a-list",
        },
    )

    assert payload["runStatus"] == "completed"
    assert payload["sourceDiagnosticCodes"] == []
    assert "core_portfolio_state_source_proof_missing" in payload["proofBlockers"]
    assert core_portfolio_state_live_proof_is_valid(payload) is False


def test_empty_core_portfolio_state_live_proof_summary_is_unknown_and_blocked() -> None:
    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_core_source_attempted=True,
        evidence_summary={},
    )

    assert payload["runStatus"] == "unknown"
    assert "core_portfolio_state_source_run_blocked" in payload["proofBlockers"]
    assert core_portfolio_state_live_proof_is_valid(payload) is False


def test_core_portfolio_state_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "core-portfolio-state-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(),
    )

    result = module.main(
        [
            "--core-query-control-plane-base-url",
            "http://localhost:8101",
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
    assert payload["portfolioStateRefPresent"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert (
        "opportunity_archetype_core_portfolio_state_source_ref_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_core_portfolio_state_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "core-portfolio-state-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: RecordingCoreSource(
            error=CoreSourceUnavailable(code="core_portfolio_state_source_unavailable")
        ),
    )

    result = module.main(
        [
            "--core-query-control-plane-base-url",
            "http://localhost:8101",
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
    assert "source_error_core_portfolio_state_source_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _portfolio_state_evidence() -> CorePortfolioStateEvidence:
    return CorePortfolioStateEvidence(
        portfolio_state_ref=SourceRef(
            product_id="lotus-core:PortfolioStateSnapshot:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/core-snapshot",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:portfolio-state",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        ),
        source_evidence_available=True,
        portfolio_state_diagnostic="core_portfolio_state_ready",
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_core_portfolio_state_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_core_portfolio_state_live_proof", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
