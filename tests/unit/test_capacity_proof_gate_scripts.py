from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture


ROOT = Path(__file__).resolve().parents[2]


class ThresholdPort:
    def __init__(self) -> None:
        self._values = iter([0.2, 0.9, 0.2])

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(next(self._values))

    def acquire_load_connection(self) -> None:
        pass

    def release_load_connections(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_postgres_capacity_threshold_proof_gate_accepts_valid_source_safe_artifact(
    tmp_path: Path,
) -> None:
    module = _load_script("postgres_capacity_threshold_proof_gate.py")
    artifact = tmp_path / "postgres-capacity-threshold-proof.json"
    artifact.write_text(json.dumps(_postgres_threshold_proof()), encoding="utf-8")

    assert module.main(["--artifact", str(artifact)]) == 0


def test_postgres_capacity_threshold_proof_gate_rejects_invalid_artifact(
    tmp_path: Path,
) -> None:
    module = _load_script("postgres_capacity_threshold_proof_gate.py")
    proof = _postgres_threshold_proof()
    proof["supportedFeaturePromoted"] = True
    artifact = tmp_path / "postgres-capacity-threshold-proof.json"
    artifact.write_text(json.dumps(proof), encoding="utf-8")

    assert module.main(["--artifact", str(artifact)]) == 1


def test_dependency_recovery_proof_gate_accepts_valid_fault_recovery_artifact(
    tmp_path: Path,
) -> None:
    module = _load_script("service_dependency_recovery_proof_gate.py")
    artifact = tmp_path / "service-dependency-recovery-proof.json"
    artifact.write_text(json.dumps(_dependency_recovery_proof()), encoding="utf-8")

    assert module.main(["--artifact", str(artifact)]) == 0


def test_dependency_recovery_proof_gate_rejects_recovery_with_errors(tmp_path: Path) -> None:
    module = _load_script("service_dependency_recovery_proof_gate.py")
    proof = _dependency_recovery_proof()
    scenario = dict(proof["scenarios"][0])  # type: ignore[index]
    scenario["errorCount"] = 1
    proof["scenarios"] = [scenario]
    artifact = tmp_path / "service-dependency-recovery-proof.json"
    artifact.write_text(json.dumps(proof), encoding="utf-8")

    assert module.main(["--artifact", str(artifact)]) == 1


def _postgres_threshold_proof() -> dict[str, Any]:
    return execute_postgres_capacity_threshold_proof(
        stress_port=ThresholdPort(),
        environment_profile="test",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="a" * 40,
        branch="main",
        run_id="threshold-1",
        maximum_load_connections=5,
    )


def _dependency_recovery_proof() -> dict[str, Any]:
    return {
        "schemaVersion": "lotus-idea.service-capacity-baseline.v1",
        "repository": "lotus-idea",
        "proofScope": "source_safe_service_capacity_baseline",
        "claimPosture": "report_only_baseline",
        "environmentProfile": "production-like",
        "commitSha": "a" * 40,
        "branch": "main",
        "runId": "dependency-proof-1",
        "scenarios": [
            {
                "scenario": "dependency_failure",
                "sampleCount": 2,
                "acceptedCount": 2,
                "errorCount": 0,
                "conflictCount": 0,
                "recoverySampleCount": 1,
                "recoverySuccessRate": 1.0,
            }
        ],
        "supportedFeaturePromoted": False,
    }


def _load_script(filename: str) -> ModuleType:
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
