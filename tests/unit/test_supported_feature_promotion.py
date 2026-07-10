from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from app.application.supported_feature_promotion import (
    NO_SUPPORTED_FEATURES_PROMOTED,
    SUPPORTED_FEATURE_PROMOTION_EVIDENCE_STALE,
    SUPPORTED_FEATURE_REGISTRY_INVALID,
    evaluate_supported_feature_promotion,
)
from tests.unit.test_supported_features_gate import (
    _base_registry,
    _valid_implemented_feature,
)

EVALUATED_AT = datetime(2026, 7, 10, tzinfo=UTC)


def test_empty_registry_is_valid_but_not_promoted(tmp_path: Path) -> None:
    path = write_registry(tmp_path, _base_registry())

    evaluation = evaluate_supported_feature_promotion(path, evaluated_at_utc=EVALUATED_AT)

    assert evaluation.registry_valid is True
    assert evaluation.promoted_feature_count == 0
    assert evaluation.supported_features_promoted is False
    assert evaluation.blocker_codes == (NO_SUPPORTED_FEATURES_PROMOTED,)
    assert evaluation.source_ref == "supported-features.json"


def test_malformed_implemented_status_cannot_promote(tmp_path: Path) -> None:
    payload = _base_registry()
    payload["features"] = [{"id": "fake-feature", "status": "implemented"}]

    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload), evaluated_at_utc=EVALUATED_AT
    )

    assert evaluation.registry_valid is False
    assert evaluation.promoted_feature_count == 0
    assert evaluation.supported_features_promoted is False
    assert evaluation.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)


def test_missing_evidence_path_cannot_promote(tmp_path: Path) -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    promotion_evidence = feature["promotion_evidence"]
    assert isinstance(promotion_evidence, dict)
    evidence = dict(promotion_evidence)
    evidence["code_modules"] = ["src/app/application/missing.py"]
    feature["promotion_evidence"] = evidence
    payload["features"] = [feature]

    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload), evaluated_at_utc=EVALUATED_AT
    )

    assert evaluation.supported_features_promoted is False
    assert evaluation.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)
    assert any("path does not exist" in error for error in evaluation.validation_errors)


def test_stale_promotion_review_has_explicit_blocker(tmp_path: Path) -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    feature["last_reviewed_utc"] = "2026-03-01T00:00:00Z"
    payload["features"] = [feature]

    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload), evaluated_at_utc=EVALUATED_AT
    )

    assert evaluation.supported_features_promoted is False
    assert evaluation.blocker_codes == (
        SUPPORTED_FEATURE_REGISTRY_INVALID,
        SUPPORTED_FEATURE_PROMOTION_EVIDENCE_STALE,
    )


def test_valid_current_implemented_feature_is_promoted(tmp_path: Path) -> None:
    payload = _base_registry()
    payload["features"] = [_valid_implemented_feature()]

    evaluation = evaluate_supported_feature_promotion(
        write_registry(tmp_path, payload), evaluated_at_utc=EVALUATED_AT
    )

    assert evaluation.registry_valid is True
    assert evaluation.promoted_feature_ids == ("advisor-review-queue",)
    assert evaluation.promoted_feature_count == 1
    assert evaluation.supported_features_promoted is True
    assert evaluation.blocker_codes == ()


def test_missing_and_invalid_json_registries_fail_closed(tmp_path: Path) -> None:
    missing = evaluate_supported_feature_promotion(
        tmp_path / "missing.json", evaluated_at_utc=EVALUATED_AT
    )
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    invalid = evaluate_supported_feature_promotion(invalid_path, evaluated_at_utc=EVALUATED_AT)

    assert missing.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)
    assert invalid.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)
    assert missing.source_ref == "missing.json"
    assert invalid.source_ref == "invalid.json"


def write_registry(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "supported-features.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
