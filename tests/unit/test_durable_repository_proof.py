from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
    REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS,
    build_durable_repository_proof_payload,
    durable_repository_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_durable_repository_proof() -> None:
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    assert proof["schemaVersion"] == DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "postgres_runtime_repository_contract"
    assert proof["proofScope"] == "repo_native_ci_runtime_proof"
    assert proof["durableRepositoryProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == ("durable_repository_not_configured",)
    assert tuple(proof["evidenceRefs"]) == REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS
    assert proof["productionStorageCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert durable_repository_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "postgresql://" not in serialized


def test_rejects_durable_repository_proof_when_evidence_is_missing(tmp_path: Path) -> None:
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["durableRepositoryProofValid"] is False
    assert durable_repository_proof_is_valid(proof) is False


def test_rejects_durable_repository_proof_with_naive_timestamp() -> None:
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["durableRepositoryProofValid"] is False
    assert durable_repository_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("durableRepositoryProofValid", False),
        ("productionStorageCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_durable_repository_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_durable_repository_proof()
    proof[field_name] = bad_value

    assert durable_repository_proof_is_valid(proof) is False


def test_durable_repository_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "durable-repository-proof.json"

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
    assert durable_repository_proof_is_valid(proof) is True


def test_durable_repository_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_durable_repository_proof() -> dict[str, object]:
    return build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_durable_repository_proof.py"
    spec = importlib.util.spec_from_file_location("generate_durable_repository_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "durable_repository_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "durable_repository_proof_contract_gate", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
