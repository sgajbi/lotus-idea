from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from app.application.ai_model_risk_operations_proof import (
    AI_MODEL_RISK_OPERATIONS_BLOCKERS_CLEARED,
    AI_MODEL_RISK_OPERATIONS_PROOF_SCHEMA_VERSION,
    EXPECTED_ALERT_IDS,
    EXPECTED_DASHBOARD_UID,
    EXPECTED_METRIC_NAME,
    REMAINING_AI_MODEL_RISK_OPERATIONS_BLOCKERS,
    REQUIRED_AI_MODEL_RISK_OPERATIONS_EVIDENCE_REFS,
    ai_model_risk_operations_proof_is_valid,
    build_ai_model_risk_operations_proof_payload,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_ai_model_risk_operations_proof() -> None:
    proof = build_ai_model_risk_operations_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )

    assert proof["schemaVersion"] == AI_MODEL_RISK_OPERATIONS_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "ai_model_risk_operations_dashboard_alert_certification"
    assert proof["proofScope"] == "source_safe_operations_artifact_certification"
    assert proof["aiModelRiskOperationsProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (AI_MODEL_RISK_OPERATIONS_BLOCKERS_CLEARED)
    assert tuple(proof["evidenceRefs"]) == REQUIRED_AI_MODEL_RISK_OPERATIONS_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_AI_MODEL_RISK_OPERATIONS_BLOCKERS
    )
    assert proof["metricFamily"] == EXPECTED_METRIC_NAME
    assert proof["dashboardUid"] == EXPECTED_DASHBOARD_UID
    assert tuple(proof["alertIds"]) == EXPECTED_ALERT_IDS
    assert proof["modelRiskDashboardCertified"] is True
    assert proof["modelRiskAlertsCertified"] is True
    assert proof["lotusAiRuntimeExecuted"] is False
    assert proof["liveProviderExecuted"] is False
    assert proof["runtimeTrustTelemetryCertified"] is False
    assert proof["workbenchProductProofCertified"] is False
    assert proof["clientReadyPublicationAuthorized"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert ai_model_risk_operations_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "clientId" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_rejects_ai_model_risk_operations_proof_with_naive_timestamp() -> None:
    proof = build_ai_model_risk_operations_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0),
        repository_root=ROOT,
    )

    assert proof["aiModelRiskOperationsProofValid"] is False
    assert ai_model_risk_operations_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-ai"),
        ("proofType", "dashboard_only"),
        ("proofScope", "provider_runtime"),
        ("aiModelRiskOperationsProofValid", False),
        ("metricFamily", "local_metric_total"),
        ("dashboardUid", "local-dashboard"),
        ("alertIds", []),
        ("modelRiskDashboardCertified", False),
        ("modelRiskAlertsCertified", False),
        ("lotusAiRuntimeExecuted", True),
        ("liveProviderExecuted", True),
        ("runtimeTrustTelemetryCertified", True),
        ("workbenchProductProofCertified", True),
        ("clientReadyPublicationAuthorized", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_ai_model_risk_operations_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_ai_model_risk_operations_proof()
    proof[field_name] = bad_value

    assert ai_model_risk_operations_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_ai_model_risk_operations_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_ai_model_risk_operations_proof()
    proof[field_name] = bad_value

    assert ai_model_risk_operations_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "dashboardArtifactCertified",
        "alertRulesArtifactCertified",
        "runbookArtifactCertified",
        "operationsContractCertified",
    ],
)
def test_rejects_ai_model_risk_operations_proof_with_invalid_proof_checks(
    check_name: str,
) -> None:
    proof = _valid_ai_model_risk_operations_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert ai_model_risk_operations_proof_is_valid(proof) is False


def test_ai_model_risk_operations_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "ai-model-risk-operations-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-26T00:00:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert ai_model_risk_operations_proof_is_valid(proof) is True


def test_ai_model_risk_operations_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_ai_model_risk_operations_proof_contract_gate_passes_current_artifacts() -> None:
    module = _load_contract_gate_script()

    assert module.validate_ai_model_risk_operations_proof_contract() == []


def _valid_ai_model_risk_operations_proof() -> dict[str, object]:
    return build_ai_model_risk_operations_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_ai_model_risk_operations_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_ai_model_risk_operations_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "ai_model_risk_operations_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "ai_model_risk_operations_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
