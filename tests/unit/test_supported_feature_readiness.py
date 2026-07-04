from __future__ import annotations

import json
from pathlib import Path

from app.application.implementation_proof_readiness import (
    _supported_feature_capability,
    _supported_feature_count,
)


def test_readiness_counts_only_implemented_supported_features(tmp_path: Path) -> None:
    registry_path = tmp_path / "supported-features.json"
    registry_path.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "id": "planned-review-queue",
                        "status": "planned",
                    },
                    {
                        "id": "not-applicable-review-queue",
                        "status": "not_applicable",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert _supported_feature_count(registry_path) == 0
    capability = _supported_feature_capability(_supported_feature_count(registry_path))
    assert capability.supported_feature_promoted is False
    assert "no_supported_features_promoted" in capability.blockers


def test_readiness_counts_implemented_supported_features(tmp_path: Path) -> None:
    registry_path = tmp_path / "supported-features.json"
    registry_path.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "id": "advisor-review-queue",
                        "status": "implemented",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert _supported_feature_count(registry_path) == 1
    capability = _supported_feature_capability(_supported_feature_count(registry_path))
    assert capability.supported_feature_promoted is True
    assert "no_supported_features_promoted" not in capability.blockers
