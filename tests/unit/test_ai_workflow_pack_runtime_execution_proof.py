from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
    REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
    REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS,
    ai_workflow_pack_runtime_execution_proof_is_valid,
    build_ai_workflow_pack_runtime_execution_proof_payload,
)
from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_runtime_execution_fixture,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_ai_workflow_pack_runtime_execution_proof(tmp_path: Path) -> None:
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path),
    )

    assert proof["schemaVersion"] == AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "lotus_ai_idea_workflow_pack_runtime_execution"
    assert proof["proofScope"] == "source_safe_runtime_execution_proof_only"
    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED
    )
    assert tuple(proof["evidenceRefs"]) == (
        REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS
    )
    assert proof["workflowPackId"] == "idea_explanation.pack@v1"
    assert proof["workflowAuthorityOwner"] == "lotus-idea"
    assert proof["aiCapabilityOwner"] == "lotus-ai"
    assert proof["workflowPackRuntimeExecutionCertified"] is True
    assert proof["lotusAiRuntimeExecuted"] is True
    assert proof["deterministicStubExecution"] is True
    assert proof["liveProviderExecuted"] is False
    assert proof["providerRolloutCertified"] is False
    assert proof["modelRiskDashboardCertified"] is False
    assert proof["modelRiskAlertsCertified"] is False
    assert proof["workbenchProductProofCertified"] is False
    assert proof["clientReadyPublicationAuthorized"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_rejects_ai_workflow_pack_runtime_execution_proof_when_ai_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=tmp_path / "missing-lotus-ai",
    )

    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert proof["proofChecks"]["fileEvidencePresent"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_rejects_ai_workflow_pack_runtime_execution_proof_with_naive_timestamp(
    tmp_path: Path,
) -> None:
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0),
        repository_root=ROOT,
        lotus_ai_root=write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path),
    )

    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-ai"),
        ("proofType", "registration"),
        ("proofScope", "provider_execution"),
        ("aiWorkflowPackRuntimeExecutionProofValid", False),
        ("workflowPackId", "other.pack@v1"),
        ("workflowAuthorityOwner", "lotus-ai"),
        ("aiCapabilityOwner", "lotus-idea"),
        ("workflowPackRuntimeExecutionCertified", False),
        ("lotusAiRuntimeExecuted", False),
        ("deterministicStubExecution", False),
        ("liveProviderExecuted", True),
        ("providerRolloutCertified", True),
        ("modelRiskDashboardCertified", True),
        ("modelRiskAlertsCertified", True),
        ("workbenchProductProofCertified", True),
        ("clientReadyPublicationAuthorized", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_ai_workflow_pack_runtime_execution_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_ai_workflow_pack_runtime_execution_proof(tmp_path)
    proof[field_name] = bad_value

    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_ai_workflow_pack_runtime_execution_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_ai_workflow_pack_runtime_execution_proof(tmp_path)
    proof[field_name] = bad_value

    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "ideaProviderStubImplemented",
        "ideaGuardrailsImplemented",
        "workflowExecutionInvokesIdeaGuardrails",
        "stubProviderRoutesIdeaPack",
        "callerPolicyAuthorizesIdeaWithoutControlPrivilege",
        "testsCoverIdeaRuntimeExecution",
    ],
)
def test_rejects_ai_workflow_pack_runtime_execution_proof_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_ai_workflow_pack_runtime_execution_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_ai_workflow_pack_runtime_execution_proof_cli_writes_valid_artifact(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "ai-workflow-pack-runtime-execution-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-26T00:00:00Z",
            "--lotus-ai-root",
            str(write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path)),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is True


def test_ai_workflow_pack_runtime_execution_proof_cli_allows_missing_evidence(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "missing-ai-runtime-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-26T00:00:00Z",
            "--lotus-ai-root",
            str(tmp_path / "missing-lotus-ai"),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert proof["proofChecks"]["fileEvidencePresent"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_ai_workflow_pack_runtime_execution_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_ai_workflow_pack_runtime_execution_proof_contract_gate_allows_missing_sibling_evidence(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()

    errors = module.validate_ai_workflow_pack_runtime_execution_proof_contract(
        lotus_ai_root=tmp_path / "missing-lotus-ai"
    )

    assert errors == []


def _valid_ai_workflow_pack_runtime_execution_proof(tmp_path: Path) -> dict[str, object]:
    return build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path),
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_ai_workflow_pack_runtime_execution_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_ai_workflow_pack_runtime_execution_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "ai_workflow_pack_runtime_execution_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "ai_workflow_pack_runtime_execution_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
