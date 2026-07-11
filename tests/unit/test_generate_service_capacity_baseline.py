from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "generate_service_capacity_baseline.py"
    spec = importlib.util.spec_from_file_location("generate_service_capacity_baseline", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _input() -> dict[str, Any]:
    return {
        "environmentProfile": "test",
        "generatedAtUtc": "2026-07-11T03:00:00Z",
        "commitSha": "abc123",
        "branch": "feature/capacity",
        "runId": "local-1",
        "observedWindowSeconds": 30.0,
        "postgresSaturationMeasured": False,
        "costResourceMeasured": False,
        "measurements": [
            {
                "scenario": "dependency_failure",
                "durationSeconds": 0.2,
                "outcome": "accepted",
                "retryCount": 2,
                "recovered": True,
            }
        ],
    }


def test_generator_maps_closed_measurement_input() -> None:
    module = _load_script()

    artifact = module.generate_service_capacity_baseline(_input())

    dependency = next(
        item for item in artifact["scenarios"] if item["scenario"] == "dependency_failure"
    )
    assert dependency["sampleCount"] == 1
    assert dependency["maxRetryCount"] == 2
    assert dependency["recoverySuccessRate"] == 1.0
    assert "dependency_recovery_evidence_missing" not in artifact["certificationBlockers"]


@pytest.mark.parametrize("field", ["payload", "tenant_id", "database_url", "url"])
def test_generator_rejects_unknown_source_bearing_top_level_fields(field: str) -> None:
    module = _load_script()
    payload = _input()
    payload[field] = "unsafe"

    with pytest.raises(ValueError, match="unknown fields"):
        module.generate_service_capacity_baseline(payload)


def test_generator_rejects_unknown_measurement_fields() -> None:
    module = _load_script()
    payload = _input()
    payload["measurements"][0]["portfolio_id"] = "unsafe"

    with pytest.raises(ValueError, match=r"measurements\[0\] contains unknown fields"):
        module.generate_service_capacity_baseline(payload)


def test_cli_writes_atomic_source_safe_artifact(tmp_path: Path) -> None:
    module = _load_script()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "nested" / "baseline.json"
    input_path.write_text(json.dumps(_input()), encoding="utf-8")

    exit_code = module.main(["--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = cast(dict[str, Any], json.loads(output_path.read_text(encoding="utf-8")))
    assert artifact["proofScope"] == "source_safe_service_capacity_baseline"
    assert not output_path.with_suffix(".json.tmp").exists()


def test_cli_fails_closed_without_writing_partial_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_script()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "baseline.json"
    input_path.write_text("[]", encoding="utf-8")

    exit_code = module.main(["--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 2
    assert not output_path.exists()
    assert "capacity input must be a JSON object" in capsys.readouterr().err
