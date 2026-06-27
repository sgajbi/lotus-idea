from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.runtime_trust_telemetry_proof import (
    REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS,
    REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS,
    RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED,
    RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION,
    build_runtime_trust_telemetry_proof_payload,
    runtime_trust_telemetry_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_runtime_trust_telemetry_proof() -> None:
    proof = _valid_runtime_trust_telemetry_proof()

    assert proof["schemaVersion"] == RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "runtime_trust_telemetry_certification"
    assert proof["proofScope"] == "source_safe_seeded_runtime_snapshot_certification"
    assert proof["runtimeTrustTelemetryProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED
    assert proof["candidateSnapshotCount"] == 1
    assert proof["currentSourceRefCount"] == 4
    assert proof["staleOrUnavailableSourceRefCount"] == 0
    assert proof["lineageMaterialized"] is True
    assert tuple(proof["evidenceRefs"]) == REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS
    )
    assert proof["platformCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert runtime_trust_telemetry_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "contentHash" not in serialized
    assert "content_hash" not in serialized


def test_rejects_runtime_trust_telemetry_proof_when_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_runtime_trust_telemetry_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["runtimeTrustTelemetryProofValid"] is False
    assert runtime_trust_telemetry_proof_is_valid(proof) is False


def test_rejects_runtime_trust_telemetry_proof_with_naive_timestamp() -> None:
    proof = build_runtime_trust_telemetry_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["runtimeTrustTelemetryProofValid"] is False
    assert runtime_trust_telemetry_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("runtimeTrustTelemetryProofValid", False),
        ("candidateSnapshotCount", 0),
        ("currentSourceRefCount", 0),
        ("staleOrUnavailableSourceRefCount", 1),
        ("lineageMaterialized", False),
        ("platformCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_runtime_trust_telemetry_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_runtime_trust_telemetry_proof()
    proof[field_name] = bad_value

    assert runtime_trust_telemetry_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_runtime_trust_telemetry_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_runtime_trust_telemetry_proof()
    proof[field_name] = bad_value

    assert runtime_trust_telemetry_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "telemetryContractExercised",
    ],
)
def test_rejects_runtime_trust_telemetry_proof_with_invalid_proof_checks(
    check_name: str,
) -> None:
    proof = _valid_runtime_trust_telemetry_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert runtime_trust_telemetry_proof_is_valid(proof) is False


def test_runtime_trust_telemetry_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "runtime-trust-telemetry-proof.json"

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
    assert runtime_trust_telemetry_proof_is_valid(proof) is True


def test_runtime_trust_telemetry_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_runtime_trust_telemetry_proof() -> dict[str, Any]:
    return build_runtime_trust_telemetry_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_runtime_trust_telemetry_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_runtime_trust_telemetry_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "runtime_trust_telemetry_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "runtime_trust_telemetry_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
