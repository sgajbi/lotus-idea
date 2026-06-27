from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.mesh_policy_proof import (
    MESH_POLICY_BLOCKERS_CLEARED,
    MESH_POLICY_PROOF_SCHEMA_VERSION,
    REMAINING_MESH_POLICY_BLOCKERS,
    REQUIRED_MESH_POLICY_EVIDENCE_REFS,
    build_mesh_policy_proof_payload,
    mesh_policy_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_mesh_policy_proof() -> None:
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )

    assert proof["schemaVersion"] == MESH_POLICY_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "mesh_policy_contract"
    assert proof["proofScope"] == "repo_owned_slo_access_evidence_policy_validation"
    assert proof["meshPolicyProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == MESH_POLICY_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_MESH_POLICY_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == REMAINING_MESH_POLICY_BLOCKERS
    assert proof["platformMeshCertified"] is False
    assert proof["producerProductsActive"] is False
    assert proof["gatewayWorkbenchDiscoveryCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert mesh_policy_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_mesh_policy_proof_with_missing_policy_files(tmp_path: Path) -> None:
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["meshPolicyProofValid"] is False
    assert proof["proofChecks"]["fileEvidencePresent"] is False
    assert mesh_policy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "mesh"),
        ("proofScope", "certified"),
        ("meshPolicyProofValid", False),
        ("platformMeshCertified", True),
        ("producerProductsActive", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", ""),
    ],
)
def test_rejects_mesh_policy_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof[field_name] = bad_value

    assert mesh_policy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", ["data_mesh_not_certified"]),
        ("evidenceRefs", ["contracts/domain-data-products/mesh-readiness.v1.json"]),
        ("remainingCertificationBlockers", ["mesh_slo_policy_certification_missing"]),
        ("proofChecks", "all-good"),
    ],
)
def test_rejects_mesh_policy_proof_with_invalid_contract_collections(
    field_name: str,
    bad_value: object,
) -> None:
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof[field_name] = bad_value

    assert mesh_policy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "readinessReferencesPolicies",
        "sloPolicyValid",
        "accessPolicyValid",
        "evidencePolicyValid",
    ],
)
def test_rejects_mesh_policy_proof_with_invalid_proof_checks(check_name: str) -> None:
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof_checks = dict(proof["proofChecks"])
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert mesh_policy_proof_is_valid(proof) is False


def test_rejects_mesh_readiness_without_source_of_truth_map(tmp_path: Path) -> None:
    _copy_mesh_policy_contracts(tmp_path)
    readiness_path = tmp_path / "contracts" / "domain-data-products" / "mesh-readiness.v1.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["source_of_truth"] = []
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["meshPolicyProofValid"] is False
    assert proof["proofChecks"]["readinessReferencesPolicies"] is False
    assert mesh_policy_proof_is_valid(proof) is False


def test_mesh_policy_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "mesh-policy-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert mesh_policy_proof_is_valid(proof) is True


def test_mesh_policy_proof_cli_rejects_naive_timestamp(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    module = _load_generator_script()

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00",
            "--output",
            str(tmp_path / "mesh-policy-proof.json"),
        ]
    )

    assert result == 2
    assert "timezone-aware" in capsys.readouterr().err


def test_mesh_policy_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_mesh_policy_proof_contract_gate_rejects_invalid_current_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_contract_gate_script()

    def invalid_proof(*, generated_at_utc: datetime, repository_root: Path) -> dict[str, Any]:
        proof = build_mesh_policy_proof_payload(
            generated_at_utc=generated_at_utc,
            repository_root=repository_root,
        )
        proof["proofChecks"] = {**dict(proof["proofChecks"]), "sloPolicyValid": False}
        return proof

    monkeypatch.setattr(module, "build_mesh_policy_proof_payload", invalid_proof)

    errors = module.validate_mesh_policy_proof_contract()

    assert "mesh policy proof must validate against current repo policy contracts" in errors


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_mesh_policy_proof.py"
    spec = importlib.util.spec_from_file_location("generate_mesh_policy_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "mesh_policy_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location("mesh_policy_proof_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_mesh_policy_contracts(target_root: Path) -> None:
    for relative_path in REQUIRED_MESH_POLICY_EVIDENCE_REFS:
        if relative_path.startswith(("GET ", "POST ", "make ")):
            continue
        source_path = ROOT / relative_path
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
