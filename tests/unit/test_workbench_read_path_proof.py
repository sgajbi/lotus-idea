from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.workbench_read_path_proof import (
    REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
    REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS,
    REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS,
    WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
    build_workbench_read_path_proof_payload,
    workbench_read_path_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_workbench_read_path_proof() -> None:
    proof = _valid_workbench_read_path_proof()

    assert proof["schemaVersion"] == WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "workbench_gateway_read_path_contract"
    assert proof["proofScope"] == "bounded_read_only_queue_detail_consumption"
    assert proof["workbenchReadPathProofValid"] is True
    assert tuple(cast(tuple[str, ...], proof["aggregateBlockersCleared"])) == (
        "workbench_gateway_bff_consumption_proof_missing",
    )
    assert (
        tuple(cast(tuple[str, ...], proof["localEvidenceRefs"]))
        == REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS
    )
    assert tuple(cast(tuple[str, ...], proof["externalEvidenceRefs"])) == (
        REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS
    )
    assert tuple(cast(tuple[str, ...], proof["remainingCertificationBlockers"])) == (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    )
    assert proof["fullWorkbenchProductCertified"] is False
    assert proof["canonicalDemoRuntimeCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert workbench_read_path_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "requestBody" not in serialized


def test_rejects_workbench_read_path_proof_when_evidence_is_missing(tmp_path: Path) -> None:
    proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["workbenchReadPathProofValid"] is False
    assert workbench_read_path_proof_is_valid(proof) is False


def test_rejects_workbench_read_path_proof_with_naive_timestamp() -> None:
    proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["workbenchReadPathProofValid"] is False
    assert workbench_read_path_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("workbenchReadPathProofValid", False),
        ("fullWorkbenchProductCertified", True),
        ("canonicalDemoRuntimeCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_workbench_read_path_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_workbench_read_path_proof()
    proof[field_name] = bad_value

    assert workbench_read_path_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("localEvidenceRefs", []),
        ("externalEvidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_workbench_read_path_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_workbench_read_path_proof()
    proof[field_name] = bad_value

    assert workbench_read_path_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "readOnlyQueueRouteRecorded",
        "readOnlyDetailRouteRecorded",
        "workbenchMergedPrRecorded",
    ],
)
def test_rejects_workbench_read_path_proof_with_invalid_proof_checks(
    check_name: str,
) -> None:
    proof = _valid_workbench_read_path_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert workbench_read_path_proof_is_valid(proof) is False


def test_workbench_read_path_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "workbench-read-path-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert workbench_read_path_proof_is_valid(proof) is True


def test_workbench_read_path_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_workbench_read_path_proof() -> dict[str, Any]:
    return build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_workbench_read_path_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_workbench_read_path_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench_read_path_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "workbench_read_path_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
