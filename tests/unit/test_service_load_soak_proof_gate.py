from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.capacity_evidence_qualification import LOAD_SOAK_SCENARIO_THRESHOLDS


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    path = ROOT / "scripts" / "service_load_soak_proof_gate.py"
    spec = importlib.util.spec_from_file_location("service_load_soak_proof_gate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, object]:
    return {
        "schemaVersion": "lotus-idea.service-capacity-baseline.v1",
        "proofScope": "source_safe_service_capacity_baseline",
        "claimPosture": "report_only_baseline",
        "environmentProfile": "production-like",
        "branch": "main",
        "supportedFeaturePromoted": False,
        "observedWindowSeconds": 3_600.0,
        "scenarios": [
            {
                "scenario": scenario,
                "sampleCount": 1_000,
                "conflictCount": 0,
                "errorRate": 0.0,
                "latencyP95Seconds": thresholds[1],
                "latencyP99Seconds": thresholds[2],
                "observationSpanSeconds": 3_600.0,
            }
            for scenario, thresholds in LOAD_SOAK_SCENARIO_THRESHOLDS.items()
        ],
    }


def test_artifact_gate_accepts_qualifying_source_safe_proof(tmp_path: Path) -> None:
    artifact = tmp_path / "proof.json"
    artifact.write_text(json.dumps(_proof()), encoding="utf-8")

    _load_gate().validate_artifact(artifact)


def test_artifact_gate_rejects_threshold_breach(tmp_path: Path) -> None:
    proof = _proof()
    proof["scenarios"][0]["observationSpanSeconds"] = 3_599.0  # type: ignore[index]
    artifact = tmp_path / "proof.json"
    artifact.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(ValueError, match="scenario api breaches qualification"):
        _load_gate().validate_artifact(artifact)


def test_artifact_gate_rejects_non_object(tmp_path: Path) -> None:
    artifact = tmp_path / "proof.json"
    artifact.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON object"):
        _load_gate().validate_artifact(artifact)
