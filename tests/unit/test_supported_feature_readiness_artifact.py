from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.application.implementation_proof_readiness as implementation_proof_readiness_application
import scripts.generate_implementation_proof_readiness as proof_report
from tests.unit.test_supported_features_gate import (
    _base_registry,
    _valid_implemented_feature,
)


def test_generated_artifact_reports_valid_supported_feature_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry = _base_registry()
    registry["features"] = [_valid_implemented_feature()]
    registry_path = tmp_path / "supported-features.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(
        implementation_proof_readiness_application,
        "SUPPORTED_FEATURES_PATH",
        registry_path,
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-07-10T00:00:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["supportedFeatureCount"] == 1
    assert payload["supportedFeaturesPromoted"] is True
    assert payload["supportedFeaturePromoted"] is True
    capability = next(
        item
        for item in payload["capabilities"]
        if item["capabilityId"] == "supported-feature-promotion"
    )
    assert capability["blockers"] == []
    assert capability["supportedFeaturePromoted"] is True
