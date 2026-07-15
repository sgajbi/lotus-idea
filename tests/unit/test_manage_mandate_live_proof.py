from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.manage_mandate_live_proof import (
    MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION,
    build_manage_mandate_live_proof_payload,
    manage_mandate_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 27)
GENERATED_AT = datetime(2026, 6, 27, 10, 10, tzinfo=UTC)


@dataclass
class RecordingManageSource:
    error: Exception | None = None

    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> ManageMandateHealthEvidence:
        if self.error is not None:
            raise self.error
        return _manage_evidence()


def test_manage_mandate_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=True,
        evaluation_summary=_valid_summary(),
    )

    assert payload["schemaVersion"] == MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["portfolioScopeConfirmed"] is True
    assert payload["manageActionRegisterReady"] is True
    assert payload["mandatePerformanceHealthSourceRefCurrent"] is True
    assert payload["mandateRiskHealthSourceRefCurrent"] is True
    assert payload["workflowDecisionCount"] == 2
    assert payload["lineageEdgeCount"] == 1
    assert payload["rebalanceExecutionAuthorityGranted"] is False
    assert payload["orderExecutionReady"] is False
    assert payload["clientPublicationReady"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
        "opportunity_archetype_mandate_performance_health_source_ref_missing",
        "opportunity_archetype_mandate_risk_health_source_ref_missing",
    ]
    assert manage_mandate_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "rebalanceRunId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_manage_mandate_live_proof_does_not_validate() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-manage",
            "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
            "evaluationOutcome": "blocked",
            "sourceEvidenceCurrent": False,
            "portfolioScopeConfirmed": False,
            "manageActionRegisterReady": False,
            "workflowDecisionCount": 0,
            "lineageEdgeCount": 0,
            "errorCode": "manage_supportability_unavailable",
            "sourceDiagnosticCodes": ["manage_supportability_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "manage_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_manage_supportability_unavailable" in payload["proofBlockers"]
    assert "manage_source_evidence_not_current" in payload["proofBlockers"]
    assert "manage_portfolio_scope_not_confirmed" in payload["proofBlockers"]
    assert "manage_action_register_not_ready" in payload["proofBlockers"]
    assert "mandate_performance_health_source_ref_missing" in payload["proofBlockers"]
    assert "mandate_risk_health_source_ref_missing" in payload["proofBlockers"]
    assert "manage_workflow_decision_evidence_missing" in payload["proofBlockers"]
    assert "manage_lineage_evidence_missing" in payload["proofBlockers"]
    assert "no_allocation_drift_mandate_candidate_generated" in payload["proofBlockers"]
    assert manage_mandate_live_proof_is_valid(payload) is False


def test_manage_mandate_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=False,
        evaluation_summary={
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "portfolioScopeConfirmed": True,
            "manageActionRegisterReady": True,
            "mandatePerformanceHealthSourceRefCurrent": True,
            "mandateRiskHealthSourceRefCurrent": True,
            "workflowDecisionCount": 2,
            "lineageEdgeCount": 1,
            "sourceDiagnosticCodes": "not-a-list",
            "reasonCodes": "not-a-list",
            "unsupportedReasons": "not-a-list",
        },
    )

    assert payload["runStatus"] == "completed"
    assert payload["sourceDiagnosticCodes"] == []
    assert payload["reasonCodes"] == []
    assert payload["unsupportedReasons"] == []
    assert "manage_portfolio_scoped_source_proof_missing" in payload["proofBlockers"]
    assert manage_mandate_live_proof_is_valid(payload) is False


def test_manage_mandate_live_proof_requires_source_owned_health_refs() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=True,
        evaluation_summary={
            **_valid_summary(),
            "mandatePerformanceHealthSourceRefCurrent": True,
            "mandateRiskHealthSourceRefCurrent": False,
        },
    )

    assert "mandate_performance_health_source_ref_missing" not in payload["proofBlockers"]
    assert "mandate_risk_health_source_ref_missing" in payload["proofBlockers"]
    assert manage_mandate_live_proof_is_valid(payload) is False


def test_manage_mandate_live_proof_rejects_store_wide_manage_posture() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=True,
        evaluation_summary={
            **_valid_summary(),
            "portfolioScopeConfirmed": False,
            "evaluationOutcome": "blocked",
            "unsupportedReasons": ["source_partial"],
        },
    )

    assert "manage_portfolio_scope_not_confirmed" in payload["proofBlockers"]
    assert "no_allocation_drift_mandate_candidate_generated" in payload["proofBlockers"]
    assert manage_mandate_live_proof_is_valid(payload) is False


def test_manage_mandate_live_proof_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_manage_mandate_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 10, 10),
            live_manage_source_attempted=True,
            evaluation_summary=_valid_summary(),
        )


def test_manage_mandate_live_proof_coerces_invalid_count_evidence_to_blockers() -> None:
    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_manage_source_attempted=True,
        evaluation_summary={
            **_valid_summary(),
            "workflowDecisionCount": True,
            "lineageEdgeCount": -1,
        },
    )

    assert payload["workflowDecisionCount"] == 0
    assert payload["lineageEdgeCount"] == 0
    assert "manage_workflow_decision_evidence_missing" in payload["proofBlockers"]
    assert "manage_lineage_evidence_missing" in payload["proofBlockers"]
    assert manage_mandate_live_proof_is_valid(payload) is False


def test_manage_mandate_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "manage-mandate-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusManageMandateHealthSourceAdapter",
        lambda _client: RecordingManageSource(),
    )

    result = module.main(
        [
            "--manage-base-url",
            "http://localhost:8350",
            "--tenant-id",
            "tenant-a",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-27",
            "--generated-at-utc",
            "2026-06-27T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-27T10:10:00Z",
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
    assert payload["liveManageSourceAttempted"] is True
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["portfolioScopeConfirmed"] is True
    assert payload["mandatePerformanceHealthSourceRefCurrent"] is True
    assert payload["mandateRiskHealthSourceRefCurrent"] is True
    assert payload["rebalanceExecutionAuthorityGranted"] is False
    assert (
        "opportunity_archetype_portfolio_scoped_manage_source_proof_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_manage_mandate_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "manage-mandate-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusManageMandateHealthSourceAdapter",
        lambda _client: RecordingManageSource(
            error=ManageSourceUnavailable(code="manage_supportability_unavailable")
        ),
    )

    result = module.main(
        [
            "--manage-base-url",
            "http://localhost:8350",
            "--tenant-id",
            "tenant-a",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-27",
            "--generated-at-utc",
            "2026-06-27T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-27T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 3
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "blocked"
    assert "source_error_manage_supportability_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _valid_summary() -> dict[str, object]:
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-manage",
        "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
        "evaluationOutcome": "candidate_created",
        "sourceEvidenceCurrent": True,
        "portfolioScopeConfirmed": True,
        "manageActionRegisterReady": True,
        "mandatePerformanceHealthSourceRefCurrent": True,
        "mandateRiskHealthSourceRefCurrent": True,
        "workflowDecisionCount": 2,
        "lineageEdgeCount": 1,
        "sourceDiagnosticCodes": ["manage_action_register_ready_portfolio_scope"],
        "reasonCodes": ["review_required"],
        "unsupportedReasons": [],
    }


def _manage_evidence() -> ManageMandateHealthEvidence:
    return ManageMandateHealthEvidence(
        workflow_decision_count=2,
        lineage_edge_count=1,
        supportability_state="ready",
        supportability_reason="action_register_available",
        freshness_bucket="current",
        portfolio_scope_confirmed=True,
        action_register_ref=SourceRef(
            product_id="lotus-manage:PortfolioActionRegister:v1",
            source_system=SourceSystem.LOTUS_MANAGE,
            product_version="v1",
            route="/api/v1/rebalance/supportability/summary",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:portfolio-action-register",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        mandate_performance_health_ref=_source_ref(
            product_id="lotus-performance:MandatePerformanceHealthContext:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            content_hash="sha256:mandate-performance-health",
        ),
        mandate_risk_health_ref=_source_ref(
            product_id="lotus-risk:MandateRiskHealthContext:v1",
            source_system=SourceSystem.LOTUS_RISK,
            content_hash="sha256:mandate-risk-health",
        ),
        manage_diagnostic="manage_action_register_ready_portfolio_scope",
    )


def _source_ref(
    *,
    product_id: str,
    source_system: SourceSystem,
    content_hash: str,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version="v1",
        route="/api/v1/rebalance/supportability/summary",
        as_of_date=AS_OF_DATE,
        generated_at_utc=GENERATED_AT,
        content_hash=content_hash,
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_manage_mandate_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_manage_mandate_live_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
