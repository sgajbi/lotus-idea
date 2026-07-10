from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

import app.application.supported_feature_promotion as promotion
from app.application.supported_feature_promotion import (
    NO_SUPPORTED_FEATURES_PROMOTED,
    SUPPORTED_FEATURE_PROMOTION_EVIDENCE_STALE,
    SUPPORTED_FEATURE_REGISTRY_INVALID,
    evaluate_supported_feature_promotion,
    validate_supported_features,
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


def test_registry_requires_aware_evaluation_time_and_object_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_supported_feature_promotion(
            write_registry(tmp_path, _base_registry()),
            evaluated_at_utc=datetime(2026, 7, 10),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_supported_features(_base_registry(), evaluated_at_utc=datetime(2026, 7, 10))

    path = tmp_path / "supported-features-list.json"
    path.write_text("[]", encoding="utf-8")
    evaluation = evaluate_supported_feature_promotion(path, evaluated_at_utc=EVALUATED_AT)

    assert evaluation.validation_errors == ("supported-features registry must be an object",)
    assert evaluation.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)


def test_registry_rejects_ambiguous_feature_and_planned_capability_shapes() -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    payload["features"] = [feature, dict(feature), "not-an-object"]
    payload["planned_capabilities"] = [
        "not-an-object",
        {"id": "missing-fields"},
        {
            "id": "Invalid ID",
            "name": "placeholder",
            "governing_rfc": "missing-rfc.md",
            "status": "implemented",
        },
    ]

    errors = validate_supported_features(payload, evaluated_at_utc=EVALUATED_AT)

    expected_fragments = (
        "duplicates an earlier feature",
        "features[2] must be an object",
        "planned_capabilities[0] must be an object",
        "planned_capabilities[1] missing fields",
        "planned_capabilities[2].id must be stable kebab-case",
        "planned_capabilities[2].name is required",
        "planned_capabilities[2].status must remain planned",
        "governing_rfc path does not exist",
    )
    for fragment in expected_fragments:
        assert any(fragment in error for error in errors), fragment


def test_implemented_feature_evidence_fails_closed_across_all_contract_layers() -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    feature.update(
        {
            "id": "Invalid ID",
            "name": "TBD",
            "governing_rfc": "missing-rfc.md",
            "last_reviewed_utc": "not-a-timestamp",
            "api_surfaces": [
                "not-an-object",
                {
                    "method": "TRACE",
                    "path": "not-an-api-path",
                    "endpoint_certification_ref": "missing-ledger.json",
                },
            ],
            "ui_surfaces": [
                "not-an-object",
                {"surface": "", "state": "supported", "evidence_ref": "README.md"},
            ],
            "source_dependencies": "not-a-list",
            "known_gaps": "not-a-list",
        }
    )
    feature["promotion_evidence"] = {
        "code_modules": "not-a-list",
        "api_contracts": [],
        "test_evidence": [
            "not-a-test-reference",
            "tests/unit/missing_test.py::test_missing",
            "tests/unit/test_supported_feature_promotion.py::test_missing",
        ],
        "runtime_evidence": ["https://evidence.example.invalid/run/334"],
        "ci_evidence": "not-an-object",
        "documentation": ["missing-document.md"],
        "runbooks": ["placeholder"],
        "proof_artifacts": [],
    }
    payload["features"] = [feature]

    errors = validate_supported_features(payload, evaluated_at_utc=EVALUATED_AT)

    expected_fragments = (
        "id must be stable kebab-case",
        "name is required",
        "governing_rfc path does not exist",
        "last_reviewed_utc must be an explicit UTC timestamp",
        "api_surfaces[0] must be an object",
        "method must be a supported HTTP method",
        "path must be an API path",
        "must reference an endpoint certification ledger operation",
        "ui_surfaces[0] must be an object",
        "ui_surfaces[1].surface is required",
        "source_dependencies must be a list",
        "known_gaps must be a list",
        "code_modules must be a list",
        "api_contracts must be a non-empty list",
        "must use tests/path.py::test_name",
        "test file does not exist",
        "test does not exist",
        "ci_evidence must be an object",
        "documentation[0] path does not exist",
        "runbooks[0] must be a non-empty, non-placeholder string",
        "proof_artifacts must be a non-empty list",
    )
    for fragment in expected_fragments:
        assert any(fragment in error for error in errors), fragment


def test_schema_absence_and_invalid_schema_json_are_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_schema = tmp_path / "missing-schema.json"
    monkeypatch.setattr(promotion, "SUPPORTED_FEATURES_SCHEMA_PATH", missing_schema)
    missing_errors = validate_supported_features(_base_registry(), evaluated_at_utc=EVALUATED_AT)

    invalid_schema = tmp_path / "invalid-schema.json"
    invalid_schema.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(promotion, "SUPPORTED_FEATURES_SCHEMA_PATH", invalid_schema)
    invalid_errors = validate_supported_features(_base_registry(), evaluated_at_utc=EVALUATED_AT)

    assert any(error.startswith("Missing ") for error in missing_errors)
    assert any("is invalid JSON" in error for error in invalid_errors)


def test_registry_envelope_and_early_exit_shapes_fail_closed() -> None:
    payload = _base_registry()
    payload.update(
        {
            "repository": None,
            "policy": "promote from design intent",
            "features": "not-a-list",
            "planned_capabilities": "not-a-list",
        }
    )

    errors = validate_supported_features(payload, evaluated_at_utc=EVALUATED_AT)

    assert "supported-features repository is required" in errors
    assert "supported-features policy must preserve implementation-backed promotion" in errors
    assert "supported-features features must be a list" in errors
    assert "planned_capabilities must be a list" in errors


@pytest.mark.parametrize(
    ("feature_update", "expected"),
    [
        ({"status": "experimental"}, "invalid status 'experimental'"),
        ({"api_surfaces": "not-a-list"}, "api_surfaces must be a list"),
        ({"promotion_evidence": "not-an-object"}, "promotion_evidence must be a structured object"),
        (
            {"promotion_evidence": {"code_modules": []}},
            "promotion_evidence missing fields",
        ),
        (
            {
                "last_reviewed_utc": "2026-07-11T00:00:01Z",
            },
            "cannot be after the evaluation time",
        ),
    ],
)
def test_feature_validation_rejects_unsupported_early_exit_shapes(
    feature_update: dict[str, object],
    expected: str,
) -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    feature.update(feature_update)
    payload["features"] = [feature]

    errors = validate_supported_features(payload, evaluated_at_utc=EVALUATED_AT)

    assert any(expected in error for error in errors)


def test_test_evidence_rejects_blank_and_unparseable_test_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid_test = tmp_path / "tests" / "invalid_test.py"
    invalid_test.parent.mkdir()
    invalid_test.write_text("def broken(:\n", encoding="utf-8")
    monkeypatch.setattr(promotion, "ROOT", tmp_path)
    errors: list[str] = []

    promotion._validate_test_reference(errors, "evidence[0]", "placeholder")
    promotion._validate_test_reference(
        errors,
        "evidence[1]",
        "tests/invalid_test.py::test_broken",
    )

    assert any("non-empty, non-placeholder" in error for error in errors)
    assert any("test file is not parseable" in error for error in errors)


def test_endpoint_ledger_absence_and_invalid_shape_are_treated_as_uncertified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing-ledger.json"
    monkeypatch.setattr(promotion, "ENDPOINT_CERTIFICATION_LEDGER_PATH", missing)
    assert promotion._endpoint_certification_operations() == set()

    malformed = tmp_path / "ledger.json"
    malformed.write_text('{"endpoints": "not-a-list"}', encoding="utf-8")
    monkeypatch.setattr(promotion, "ENDPOINT_CERTIFICATION_LEDGER_PATH", malformed)
    assert promotion._endpoint_certification_operations() == set()


def test_feature_evidence_rejects_placeholder_gaps_and_empty_test_proof() -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    feature["known_gaps"] = ["placeholder"]
    evidence = feature["promotion_evidence"]
    assert isinstance(evidence, dict)
    evidence["test_evidence"] = []
    payload["features"] = [feature]

    errors = validate_supported_features(payload, evaluated_at_utc=EVALUATED_AT)

    assert any(
        "known_gaps[0] must be a non-empty, non-placeholder string" in error for error in errors
    )
    assert any("test_evidence must be a non-empty list" in error for error in errors)


def write_registry(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "supported-features.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
