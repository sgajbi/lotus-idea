from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.domain.proof_evidence import EvidenceClass
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS,
    REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS,
    build_gateway_workbench_contract_proof_payload,
    gateway_workbench_contract_proof_is_valid,
)
from app.application.workbench.read_path_source_contract import (
    build_workbench_read_path_source_contract_proof_payload,
)


ROOT = Path(__file__).resolve().parents[3]


def test_builds_source_safe_gateway_workbench_contract_proof() -> None:
    proof = _valid_gateway_workbench_contract_proof()

    assert proof["schemaVersion"] == GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "gateway_workbench_contract"
    assert proof["proofScope"] == "source_contract_declaration"
    assert proof["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert proof["gatewayWorkbenchContractProofValid"] is True
    assert tuple(cast(tuple[str, ...], proof["aggregateBlockersCleared"])) == (
        GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED
    )
    assert tuple(cast(tuple[str, ...], proof["localEvidenceRefs"])) == (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS
    )
    assert tuple(cast(tuple[str, ...], proof["declaredRouteRefs"])) == (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS
    )
    assert tuple(cast(tuple[str, ...], proof["remainingCertificationBlockers"])) == (
        REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS
    )
    assert proof["sourceIngestionSupported"] is False
    assert proof["outboxDeliverySupported"] is False
    assert proof["fullWorkbenchProductCertified"] is False
    assert proof["gatewayWorkbenchDiscoveryCertified"] is False
    assert proof["canonicalDemoRuntimeCertified"] is False
    assert proof["runtimeExecutionObserved"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert gateway_workbench_contract_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "requestBody" not in serialized


def test_rejects_gateway_workbench_contract_proof_without_read_path_proof() -> None:
    proof = build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_source_contract_proof=None,
        workbench_read_path_source_contract_proof_ref=None,
    )

    assert proof["gatewayWorkbenchContractProofValid"] is False
    assert gateway_workbench_contract_proof_is_valid(proof) is False


def test_rejects_gateway_workbench_contract_proof_when_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
        workbench_read_path_source_contract_proof=_valid_read_path_source_contract_proof(),
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )

    assert proof["gatewayWorkbenchContractProofValid"] is False
    assert gateway_workbench_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("gatewayWorkbenchContractProofValid", False),
        ("sourceIngestionSupported", True),
        ("outboxDeliverySupported", True),
        ("fullWorkbenchProductCertified", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("canonicalDemoRuntimeCertified", True),
        ("runtimeExecutionObserved", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("workbenchReadPathSourceContractProofRef", None),
    ],
)
def test_rejects_gateway_workbench_contract_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_gateway_workbench_contract_proof()
    proof[field_name] = bad_value

    assert gateway_workbench_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", ["gateway_workbench_proof_missing"]),
        ("localEvidenceRefs", []),
        ("declaredRouteRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_gateway_workbench_contract_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_gateway_workbench_contract_proof()
    proof[field_name] = bad_value

    assert gateway_workbench_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "workbenchReadPathSourceContractProofValid",
        "readOnlyQueueRouteDeclared",
        "readOnlyDetailRouteDeclared",
    ],
)
def test_rejects_gateway_workbench_contract_proof_with_invalid_proof_checks(
    check_name: str,
) -> None:
    proof = _valid_gateway_workbench_contract_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert gateway_workbench_contract_proof_is_valid(proof) is False


def test_gateway_workbench_contract_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    read_path_proof = tmp_path / "read-path-source-contract-proof.json"
    read_path_proof.write_text(
        json.dumps(_valid_read_path_source_contract_proof()),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "gateway-workbench-contract-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--workbench-read-path-source-contract-proof",
            str(read_path_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert gateway_workbench_contract_proof_is_valid(proof) is True


def test_gateway_workbench_contract_proof_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_gateway_workbench_contract_proof() -> dict[str, Any]:
    return build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_source_contract_proof=_valid_read_path_source_contract_proof(),
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )


def _valid_read_path_source_contract_proof() -> dict[str, Any]:
    return build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / "generate_contract_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_workbench_contract_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / "contract_proof_gate.py"
    spec = importlib.util.spec_from_file_location(
        "workbench_contract_proof_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
