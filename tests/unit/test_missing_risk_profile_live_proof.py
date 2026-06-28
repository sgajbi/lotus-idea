from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.missing_risk_profile_live_proof import (
    MISSING_RISK_PROFILE_LIVE_PROOF_SCHEMA_VERSION,
    build_missing_risk_profile_live_proof_payload,
    missing_risk_profile_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 28)
GENERATED_AT = datetime(2026, 6, 28, 10, 10, tzinfo=UTC)


@dataclass
class RecordingAdviseSource(AdviseOpportunitySourcePort):
    error: Exception | None = None

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        if self.error is not None:
            raise self.error
        return _advise_evidence()


def test_missing_risk_profile_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_missing_risk_profile_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "sourceDiagnosticCodes": ["risk_profile_missing"],
            "reasonCodes": ["missing_risk_profile", "review_required"],
            "unsupportedReasons": [],
        },
    )

    assert payload["schemaVersion"] == MISSING_RISK_PROFILE_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["adviseRiskProfileDiagnosticReady"] is True
    assert payload["riskProfileAuthorityGranted"] is False
    assert payload["suitabilityAuthorityGranted"] is False
    assert payload["policyApprovalGranted"] is False
    assert payload["proposalApprovalGranted"] is False
    assert payload["clientPublicationReady"] is False
    assert payload["typedRiskProfileSourceProductCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_advise_risk_profile_live_source_proof_missing"
    ]
    assert missing_risk_profile_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "evaluationId" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_missing_risk_profile_live_proof_does_not_validate() -> None:
    payload = build_missing_risk_profile_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "blocked",
            "sourceEvidenceCurrent": False,
            "errorCode": "advise_policy_workflow_unavailable",
            "sourceDiagnosticCodes": ["advise_policy_workflow_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "advise_risk_profile_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_advise_policy_workflow_unavailable" in payload["proofBlockers"]
    assert "advise_risk_profile_source_evidence_not_current" in payload["proofBlockers"]
    assert "advise_risk_profile_diagnostic_not_ready" in payload["proofBlockers"]
    assert "no_missing_risk_profile_candidate_generated" in payload["proofBlockers"]
    assert missing_risk_profile_live_proof_is_valid(payload) is False


def test_missing_risk_profile_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_missing_risk_profile_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_advise_source_attempted=False,
        evaluation_summary={
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "sourceDiagnosticCodes": ["risk_profile_missing"],
            "reasonCodes": "not-a-list",
            "unsupportedReasons": "not-a-list",
        },
    )

    assert payload["runStatus"] == "completed"
    assert payload["reasonCodes"] == []
    assert payload["unsupportedReasons"] == []
    assert "advise_risk_profile_live_source_proof_missing" in payload["proofBlockers"]
    assert missing_risk_profile_live_proof_is_valid(payload) is False


def test_missing_risk_profile_live_proof_rejects_generic_suitability_context() -> None:
    payload = build_missing_risk_profile_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "not_eligible",
            "sourceEvidenceCurrent": True,
            "sourceDiagnosticCodes": ["advise_policy_requirements_open"],
            "reasonCodes": ["below_materiality"],
            "unsupportedReasons": [],
        },
    )

    assert "advise_risk_profile_diagnostic_not_ready" in payload["proofBlockers"]
    assert "no_missing_risk_profile_candidate_generated" in payload["proofBlockers"]
    assert missing_risk_profile_live_proof_is_valid(payload) is False


def test_missing_risk_profile_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "missing-risk-profile-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusAdvisePolicyEvaluationSourceAdapter",
        lambda _client: RecordingAdviseSource(),
    )

    result = module.main(
        [
            "--advise-base-url",
            "http://localhost:8340",
            "--evaluation-id",
            "advise-policy-evaluation:demo-001",
            "--as-of-date",
            "2026-06-28",
            "--generated-at-utc",
            "2026-06-28T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-28T10:10:00Z",
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
    assert payload["liveAdviseSourceAttempted"] is True
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["adviseRiskProfileDiagnosticReady"] is True
    assert payload["riskProfileAuthorityGranted"] is False
    assert (
        "opportunity_archetype_advise_risk_profile_live_source_proof_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "advise-policy-evaluation:demo-001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_missing_risk_profile_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "missing-risk-profile-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusAdvisePolicyEvaluationSourceAdapter",
        lambda _client: RecordingAdviseSource(
            error=AdviseSourceUnavailable(code="advise_policy_workflow_unavailable")
        ),
    )

    result = module.main(
        [
            "--advise-base-url",
            "http://localhost:8340",
            "--evaluation-id",
            "advise-policy-evaluation:demo-001",
            "--as-of-date",
            "2026-06-28",
            "--generated-at-utc",
            "2026-06-28T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-28T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 3
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "blocked"
    assert "source_error_advise_policy_workflow_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "advise-policy-evaluation:demo-001" not in json.dumps(payload)


def _advise_evidence() -> AdvisePolicyEvaluationEvidence:
    return AdvisePolicyEvaluationEvidence(
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=1,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=0,
        client_ready_publication="BLOCKED",
        policy_ref=SourceRef(
            product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            source_system=SourceSystem.LOTUS_ADVISE,
            product_version="v1",
            route="/advisory/policy-evaluations/demo/workflow",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:advisory-risk-profile-diagnostic",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        advise_diagnostic="risk_profile_missing",
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_missing_risk_profile_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_missing_risk_profile_live_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
