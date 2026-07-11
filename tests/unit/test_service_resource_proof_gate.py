from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    path = ROOT / "scripts" / "service_resource_proof_gate.py"
    spec = importlib.util.spec_from_file_location("service_resource_proof_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, object]:
    return {
        "schemaVersion": "lotus-idea.service-resource-baseline.v1",
        "repository": "lotus-idea",
        "proofScope": "source_safe_process_resource_observation",
        "claimPosture": "report_only_resource_observation",
        "environmentProfile": "production-like",
        "commitSha": "a" * 40,
        "branch": "main",
        "runId": "resource-proof-1",
        "observedWindowSeconds": 3_600.0,
        "sampleCount": 61,
        "cpuCoreSecondsPerSecondAverage": 0.5,
        "residentMemoryBytesAverage": 100,
        "residentMemoryBytesMax": 120,
        "virtualMemoryBytesMax": 200,
        "openFileDescriptorUtilizationMax": 0.1,
        "costAttributionVerified": False,
        "resourceAttestationVerified": False,
        "certificationReady": False,
        "certificationBlockers": [
            "production_like_resource_attestation_missing",
            "cost_attribution_evidence_missing",
        ],
        "supportedFeaturePromoted": False,
    }


def test_resource_proof_gate_accepts_qualifying_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "resource.json"
    artifact.write_text(json.dumps(_proof()), encoding="utf-8")

    _load_gate().validate_artifact(artifact)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"sampleCount": 60}, "minimum sample count"),
        ({"observedWindowSeconds": 3_599.0}, "minimum observation window"),
        ({"costAttributionVerified": True}, "must not claim cost attribution"),
    ],
)
def test_resource_proof_gate_rejects_unqualified_artifact(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    artifact = tmp_path / "resource.json"
    artifact.write_text(json.dumps({**_proof(), **mutation}), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _load_gate().validate_artifact(artifact)


def test_resource_proof_gate_rejects_non_object(tmp_path: Path) -> None:
    artifact = tmp_path / "resource.json"
    artifact.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON object"):
        _load_gate().validate_artifact(artifact)
