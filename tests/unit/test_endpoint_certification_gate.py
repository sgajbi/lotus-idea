from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_endpoint_certification_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_certification_gate.py"
    spec = importlib.util.spec_from_file_location("endpoint_certification_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_endpoint_certification_gate_passes_current_repository_contract() -> None:
    module = _load_endpoint_certification_gate()

    assert module.main() == 0


def test_endpoint_certification_gate_blocks_missing_capability() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use for internal review recording.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_certified_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "certified endpoint must name at least one idea.* capability"
    ) in errors


def test_endpoint_certification_gate_blocks_weak_unsupported_boundary() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": "Do not use as a supported-feature promotion.",
        "error_examples": ["403 returns product-safe Problem Details."],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_certified_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "when_not_to_use must explicitly preserve `Gateway` boundary"
    ) in errors
    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "when_not_to_use must explicitly preserve `Workbench` boundary"
    ) in errors


def test_endpoint_certification_gate_blocks_missing_operation_event_evidence() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_review_workflow_api.py::test_review_action_api_persists_suppression_with_audit_posture"
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_certified_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "certified endpoint must reference bounded operation-event test evidence"
    ) in errors


def test_endpoint_certification_gate_accepts_operation_event_evidence() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events"
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_certified_endpoint_posture(endpoint)

    assert errors == []


def test_endpoint_certification_gate_validates_test_references() -> None:
    module = _load_endpoint_certification_gate()

    missing_file = module._validate_test_reference(
        ("GET", "/metadata"),
        "tests/integration/test_missing.py::test_metadata_endpoint",
    )
    missing_test = module._validate_test_reference(
        ("GET", "/metadata"),
        "tests/e2e/test_smoke.py::test_missing_endpoint",
    )

    assert "('GET', '/metadata'): test_evidence file does not exist" in missing_file[0]
    assert (
        "('GET', '/metadata'): test_evidence test does not exist: "
        "tests/e2e/test_smoke.py::test_missing_endpoint"
    ) in missing_test


def test_endpoint_certification_gate_validates_json_examples() -> None:
    module = _load_endpoint_certification_gate()

    errors = module._parse_json_examples(
        operation=("POST", "/api/v1/example"),
        field="response_examples",
        examples=['{"supportedFeaturePromoted": false}', '{"broken": }'],
    )

    assert "('POST', '/api/v1/example'): response_examples[1] must be valid JSON" in errors[0]
