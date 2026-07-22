from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from app.application.workbench.owner_mainline_evidence import (
    OWNER_MAINLINE_AGGREGATE_BLOCKERS_CLEARED,
    OWNER_MAINLINE_EVIDENCE_CONTRACT_REF,
    OWNER_MAINLINE_EVIDENCE_DEPENDENCY_POSTURE,
    OWNER_MAINLINE_EVIDENCE_LOCAL_REFS,
    OWNER_MAINLINE_EVIDENCE_OWNER_PROOFS,
    OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION,
    OWNER_MAINLINE_EVIDENCE_SLICE_IDS,
    OWNER_MAINLINE_EVIDENCE_TRACKING_ISSUES,
    REMAINING_OWNER_MAINLINE_CERTIFICATION_BLOCKERS,
    owner_mainline_evidence_contract_is_valid,
    validate_owner_mainline_evidence_contract,
)
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[3]


def test_checked_in_owner_mainline_evidence_contract_is_valid() -> None:
    payload = _checked_in_contract()

    assert payload["schemaVersion"] == OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION
    assert payload["repository"] == "lotus-idea"
    assert payload["rfc"] == "RFC-0002"
    assert payload["proofType"] == "rfc0002_slice11_owner_mainline_evidence"
    assert payload["proofScope"] == "owner_repo_mainline_evidence_index"
    assert payload["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert tuple(_array(payload, "sliceIds")) == OWNER_MAINLINE_EVIDENCE_SLICE_IDS
    assert tuple(_array(payload, "trackingIssues")) == OWNER_MAINLINE_EVIDENCE_TRACKING_ISSUES
    assert tuple(_array(payload, "ownerEvidence")) == OWNER_MAINLINE_EVIDENCE_OWNER_PROOFS
    assert tuple(_array(payload, "dependencyPosture")) == OWNER_MAINLINE_EVIDENCE_DEPENDENCY_POSTURE
    assert tuple(_array(payload, "localEvidenceRefs")) == OWNER_MAINLINE_EVIDENCE_LOCAL_REFS
    assert tuple(_array(payload, "remainingCertificationBlockers")) == (
        REMAINING_OWNER_MAINLINE_CERTIFICATION_BLOCKERS
    )
    assert tuple(_array(payload, "aggregateBlockersCleared")) == (
        OWNER_MAINLINE_AGGREGATE_BLOCKERS_CLEARED
    )
    assert payload["gatewayOwnerMainlineValidated"] is True
    assert payload["workbenchOwnerMainlineValidated"] is True
    assert payload["productionIdentityImplemented"] is False
    assert payload["canonicalRuntimeCertified"] is False
    assert payload["browserAccessibilityCertified"] is False
    assert payload["dataProductCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["runtimeExecutionObserved"] is False
    assert payload["proofClosed"] is False
    assert owner_mainline_evidence_contract_is_valid(payload, repository_root=ROOT) is True


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("recordedAtUtc", "not-a-datetime"),
        ("rfc", "RFC-0003"),
        ("proofType", "runtime_execution"),
        ("proofScope", "product_certification"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("ownerMainlineEvidenceValid", False),
        ("gatewayOwnerMainlineValidated", False),
        ("workbenchOwnerMainlineValidated", False),
        ("productionIdentityImplemented", True),
        ("canonicalRuntimeCertified", True),
        ("browserAccessibilityCertified", True),
        ("dataProductCertified", True),
        ("supportedFeaturePromoted", True),
        ("runtimeExecutionObserved", True),
        ("proofClosed", True),
    ],
)
def test_rejects_claim_inflation_or_wrong_top_level_values(
    field_name: str,
    bad_value: object,
) -> None:
    payload = _checked_in_contract()
    payload[field_name] = bad_value

    assert owner_mainline_evidence_contract_is_valid(payload, repository_root=ROOT) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "sliceIds",
        "trackingIssues",
        "ownerEvidence",
        "dependencyPosture",
        "localEvidenceRefs",
        "remainingCertificationBlockers",
    ],
)
def test_rejects_missing_or_changed_contract_arrays(field_name: str) -> None:
    payload = _checked_in_contract()
    payload[field_name] = []

    assert owner_mainline_evidence_contract_is_valid(payload, repository_root=ROOT) is False


def test_rejects_owner_sha_drift() -> None:
    payload = _checked_in_contract()
    owner_evidence = list(_array(payload, "ownerEvidence"))
    gateway = dict(cast(dict[str, object], owner_evidence[0]))
    gateway["mergedMainCommitSha"] = "bad-sha"
    owner_evidence[0] = gateway
    payload["ownerEvidence"] = owner_evidence

    assert owner_mainline_evidence_contract_is_valid(payload, repository_root=ROOT) is False


def test_rejects_false_blocker_clearance() -> None:
    payload = _checked_in_contract()
    payload["aggregateBlockersCleared"] = ["gateway_workbench_proof_missing"]

    assert owner_mainline_evidence_contract_is_valid(payload, repository_root=ROOT) is False


def test_rejects_unknown_fields() -> None:
    payload = _checked_in_contract()
    payload["demoReady"] = True

    errors = validate_owner_mainline_evidence_contract(payload, repository_root=ROOT)

    assert "unknown top-level owner-mainline evidence fields: ['demoReady']" in errors


def test_gate_script_accepts_checked_in_contract() -> None:
    module = _load_gate_script()

    assert module.main() == 0


def test_gate_script_rejects_forbidden_source_sensitive_content(tmp_path: Path) -> None:
    module = _load_gate_script()
    payload = _checked_in_contract()
    owner_evidence = _array(payload, "ownerEvidence")
    first_owner_evidence = cast(dict[str, object], owner_evidence[0])
    first_owner_evidence["sourceRoute"] = "/source/PB_SG_GLOBAL_BAL_001"
    path = tmp_path / "owner-mainline-evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_owner_mainline_evidence_file(path)

    assert "$.ownerEvidence[0].sourceRoute: forbidden source-sensitive key is present" in errors
    assert any("PB_SG_GLOBAL_BAL_001" in error for error in errors)


def _checked_in_contract() -> dict[str, Any]:
    payload = json.loads((ROOT / OWNER_MAINLINE_EVIDENCE_CONTRACT_REF).read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def _array(payload: dict[str, Any], field_name: str) -> list[Any]:
    value = payload[field_name]
    assert isinstance(value, list)
    return value


def _load_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / "owner_mainline_evidence_gate.py"
    spec = importlib.util.spec_from_file_location(
        "workbench_owner_mainline_evidence_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
