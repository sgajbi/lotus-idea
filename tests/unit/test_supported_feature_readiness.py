from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from app.application.implementation_proof_readiness import _supported_feature_capability
from app.application.supported_feature_promotion import (
    NO_SUPPORTED_FEATURES_PROMOTED,
    SUPPORTED_FEATURE_REGISTRY_INVALID,
    evaluate_supported_feature_promotion,
)
from tests.unit.test_supported_features_gate import (
    _base_registry,
    _valid_implemented_feature,
)

EVALUATED_AT = datetime(2026, 7, 10, tzinfo=UTC)


def test_readiness_preserves_empty_foundation_posture(tmp_path: Path) -> None:
    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, _base_registry()),
        evaluated_at_utc=EVALUATED_AT,
    )

    capability = _supported_feature_capability(evaluation)

    assert capability.supported_feature_promoted is False
    assert capability.blockers == (NO_SUPPORTED_FEATURES_PROMOTED,)
    assert capability.readiness_status == "blocked"
    assert capability.supportability_status == "not_certified"


def test_readiness_rejects_status_only_implemented_feature(tmp_path: Path) -> None:
    payload = _base_registry()
    payload["features"] = [{"id": "advisor-review-queue", "status": "implemented"}]
    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload),
        evaluated_at_utc=EVALUATED_AT,
    )

    capability = _supported_feature_capability(evaluation)

    assert evaluation.promoted_feature_count == 0
    assert capability.supported_feature_promoted is False
    assert capability.blockers == (SUPPORTED_FEATURE_REGISTRY_INVALID,)
    assert capability.evidence_refs[0] == "supported-features.json"


def test_readiness_promotes_only_valid_current_evidence(tmp_path: Path) -> None:
    payload = _base_registry()
    payload["features"] = [_valid_implemented_feature()]
    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload),
        evaluated_at_utc=EVALUATED_AT,
    )

    capability = _supported_feature_capability(evaluation)

    assert evaluation.promoted_feature_count == 1
    assert capability.supported_feature_promoted is True
    assert capability.blockers == ()
    assert capability.readiness_status == "ready"
    assert capability.supportability_status == "supported"


def write_registry(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "supported-features.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
