from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.data_mesh.mesh_policy_source_contract import (
    MESH_POLICY_SOURCE_AUTHORITY_REFS,
    MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
    MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION,
    REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS,
    REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS,
    build_mesh_policy_source_contract_payload,
    mesh_policy_source_contract_is_valid,
)


ROOT = Path(__file__).resolve().parents[3]


def test_builds_digest_bound_mesh_policy_source_contract() -> None:
    proof = _build_proof(ROOT)

    assert proof["schemaVersion"] == MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "mesh_policy_source_contract"
    assert proof["evidenceClass"] == "source_contract"
    assert proof["sourceContractValid"] is True
    assert tuple(proof["sourceContractBlockersSatisfied"]) == (
        MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS
    )
    assert tuple(item["ref"] for item in proof["sourceAuthority"]) == (
        MESH_POLICY_SOURCE_AUTHORITY_REFS
    )
    assert all(len(item["sha256"]) == 64 for item in proof["sourceAuthority"])
    assert mesh_policy_source_contract_is_valid(proof) is True


def test_source_contract_preserves_every_policy_certification_blocker() -> None:
    proof = _build_proof(ROOT)

    assert proof["sourceContractBlockersSatisfied"] == ()
    assert {
        "mesh_slo_policy_certification_missing",
        "mesh_access_policy_certification_missing",
        "mesh_evidence_policy_certification_missing",
    } <= set(proof["remainingCertificationBlockers"])
    assert proof["policyCertificationObserved"] is False
    assert proof["productionCertificationGranted"] is False


def test_rejects_missing_policy_sources(tmp_path: Path) -> None:
    proof = _build_proof(tmp_path)

    assert proof["sourceContractValid"] is False
    assert proof["contractChecks"]["sourceAuthorityDigestBound"] is False
    assert mesh_policy_source_contract_is_valid(proof) is False


def test_policy_source_mutation_changes_bound_digest(tmp_path: Path) -> None:
    _copy_mesh_policy_sources(tmp_path)
    before = _build_proof(tmp_path)
    source_path = tmp_path / MESH_POLICY_SOURCE_AUTHORITY_REFS[1]
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["description"] = "mutated declaration"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    after = _build_proof(tmp_path)

    assert before["sourceAuthority"][1]["sha256"] != after["sourceAuthority"][1]["sha256"]
    assert mesh_policy_source_contract_is_valid(after) is True


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-platform"),
        ("proofType", "mesh_policy_certification"),
        ("proofScope", "production_certification"),
        ("evidenceClass", "runtime_execution"),
        ("sourceContractValid", False),
        ("generatedAtUtc", "not-a-datetime"),
        ("policyCertificationObserved", True),
        ("platformMeshCertified", True),
        ("producerProductsActive", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("deploymentObserved", True),
        ("productionCertificationGranted", True),
        ("supportedFeaturePromoted", True),
        ("certificationClosed", True),
    ],
)
def test_rejects_claim_inflation(field_name: str, bad_value: object) -> None:
    proof = _build_proof(ROOT)
    proof[field_name] = bad_value

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_unknown_top_level_field() -> None:
    proof = _build_proof(ROOT)
    proof["certifierApproval"] = "approved"

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_unknown_contract_check() -> None:
    proof = _build_proof(ROOT)
    proof["contractChecks"] = {**proof["contractChecks"], "runtimeValidated": True}

    assert mesh_policy_source_contract_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("sourceContractBlockersSatisfied", ["mesh_slo_policy_certification_missing"]),
        ("evidenceRefs", [MESH_POLICY_SOURCE_AUTHORITY_REFS[0]]),
        ("remainingCertificationBlockers", ["data_mesh_not_certified"]),
        ("contractChecks", "all-good"),
    ],
)
def test_rejects_invalid_contract_collections(field_name: str, bad_value: object) -> None:
    proof = _build_proof(ROOT)
    proof[field_name] = bad_value

    assert mesh_policy_source_contract_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "readinessReferencesPolicies",
        "sloPolicyValid",
        "accessPolicyValid",
        "evidencePolicyValid",
    ],
)
def test_rejects_failed_contract_check(check_name: str) -> None:
    proof = _build_proof(ROOT)
    proof["contractChecks"] = {**proof["contractChecks"], check_name: False}

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_source_authority_substitution() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"][0]["repository"] = "lotus-platform"

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_missing_source_authority_entry() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"] = proof["sourceAuthority"][:-1]

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_source_authority_ref_substitution() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"][0]["ref"] = "contracts/mesh-slo/other.json"

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_non_hex_source_authority_digest() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"][0]["sha256"] = "g" * 64

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_truncated_source_authority_digest() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"][0]["sha256"] = "a" * 63

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_unknown_source_authority_field() -> None:
    proof = _build_proof(ROOT)
    proof["sourceAuthority"][0]["certifier"] = "lotus-idea"

    assert mesh_policy_source_contract_is_valid(proof) is False


def test_rejects_readiness_without_source_of_truth_map(tmp_path: Path) -> None:
    _copy_mesh_policy_sources(tmp_path)
    readiness_path = tmp_path / MESH_POLICY_SOURCE_AUTHORITY_REFS[0]
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["source_of_truth"] = []
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

    proof = _build_proof(tmp_path)

    assert proof["sourceContractValid"] is False
    assert proof["contractChecks"]["readinessReferencesPolicies"] is False
    assert mesh_policy_source_contract_is_valid(proof) is False


def test_cli_writes_valid_source_contract(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "mesh-policy-source-contract.json"

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
    assert mesh_policy_source_contract_is_valid(proof) is True


def test_cli_rejects_naive_timestamp(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    module = _load_generator_script()

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00",
            "--output",
            str(tmp_path / "mesh-policy-source-contract.json"),
        ]
    )

    assert result == 2
    assert "timezone-aware" in capsys.readouterr().err


def test_contract_gate_rejects_invalid_current_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_contract_gate_script()

    def invalid_proof(*, generated_at_utc: datetime, repository_root: Path) -> dict[str, Any]:
        proof = build_mesh_policy_source_contract_payload(
            generated_at_utc=generated_at_utc,
            repository_root=repository_root,
        )
        proof["contractChecks"] = {
            **proof["contractChecks"],
            "sloPolicyValid": False,
        }
        return proof

    monkeypatch.setattr(module, "build_mesh_policy_source_contract_payload", invalid_proof)

    errors = module.validate_mesh_policy_source_contract()

    assert "mesh policy source contract must validate against current policy sources" in errors


def test_source_contract_evidence_refs_use_capability_owned_gate() -> None:
    assert "make mesh-policy-source-contract-proof-gate" in (
        REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS
    )
    assert all(
        "mesh-policy-proof" not in ref for ref in REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS
    )


def _build_proof(repository_root: Path) -> dict[str, Any]:
    return build_mesh_policy_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=repository_root,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "data_mesh" / "generate_mesh_policy_source_contract.py"
    spec = importlib.util.spec_from_file_location(
        "generate_mesh_policy_source_contract", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "data_mesh" / "mesh_policy_source_contract_gate.py"
    spec = importlib.util.spec_from_file_location("mesh_policy_source_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_mesh_policy_sources(target_root: Path) -> None:
    for relative_path in MESH_POLICY_SOURCE_AUTHORITY_REFS:
        source_path = ROOT / relative_path
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(source_path.read_bytes())
