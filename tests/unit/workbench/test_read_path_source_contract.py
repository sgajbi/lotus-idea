from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.workbench.read_path_source_contract import (
    REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
    REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS,
    REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS,
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    build_workbench_read_path_source_contract_proof_payload,
    workbench_read_path_source_contract_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[3]


def test_builds_source_safe_workbench_read_path_source_contract() -> None:
    proof = _valid_proof()

    assert proof["schemaVersion"] == WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "workbench_gateway_read_path_source_contract"
    assert proof["proofScope"] == "bounded_read_only_queue_detail_declaration"
    assert proof["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert proof["workbenchReadPathSourceContractValid"] is True
    assert tuple(cast(tuple[str, ...], proof["aggregateBlockersCleared"])) == (
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED
    )
    assert tuple(cast(tuple[str, ...], proof["localEvidenceRefs"])) == (
        REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS
    )
    assert tuple(cast(tuple[str, ...], proof["declaredRouteRefs"])) == (
        REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS
    )
    assert tuple(cast(tuple[str, ...], proof["remainingCertificationBlockers"])) == (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    )
    assert workbench_read_path_source_contract_proof_is_valid(proof) is True
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(proof)


def test_fails_closed_when_source_evidence_is_missing(tmp_path: Path) -> None:
    proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["workbenchReadPathSourceContractValid"] is False
    assert workbench_read_path_source_contract_proof_is_valid(proof) is False


def test_fails_closed_for_naive_timestamp() -> None:
    proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["workbenchReadPathSourceContractValid"] is False
    assert workbench_read_path_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("workbenchReadPathSourceContractValid", False),
        ("gatewayServingObserved", True),
        ("workbenchConsumptionObserved", True),
        ("entitlementEnforcementObserved", True),
        ("runtimeExecutionObserved", True),
        ("browserAccessibilityCertified", True),
        ("canonicalDemoRuntimeCertified", True),
        ("fullWorkbenchProductCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_claim_inflation(field_name: str, bad_value: object) -> None:
    proof = _valid_proof()
    proof[field_name] = bad_value

    assert workbench_read_path_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", ["workbench_gateway_bff_consumption_proof_missing"]),
        ("localEvidenceRefs", []),
        ("declaredRouteRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_invalid_contract_fields(field_name: str, bad_value: object) -> None:
    proof = _valid_proof()
    proof[field_name] = bad_value

    assert workbench_read_path_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "readOnlyQueueRouteDeclared",
        "readOnlyDetailRouteDeclared",
    ],
)
def test_rejects_invalid_proof_checks(check_name: str) -> None:
    proof = _valid_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert workbench_read_path_source_contract_proof_is_valid(proof) is False


def test_generator_writes_valid_source_contract(tmp_path: Path) -> None:
    module = _load_script("generate_read_path_source_contract.py")
    output_path = tmp_path / "proof" / "read-path-source-contract-proof.json"

    result = module.main(
        ["--generated-at-utc", "2026-06-21T10:10:00Z", "--output", str(output_path)]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert workbench_read_path_source_contract_proof_is_valid(proof) is True


def test_contract_gate_scans_tuple_content() -> None:
    module = _load_script("read_path_source_contract_gate.py")
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_proof() -> dict[str, Any]:
    return build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_script(filename: str) -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
