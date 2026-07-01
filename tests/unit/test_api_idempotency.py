from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.api.idempotency import (
    IDEMPOTENCY_KEY_REQUIRED_MESSAGE,
    mark_required_idempotency_openapi_headers,
    validate_idempotency_key,
)

ROOT = Path(__file__).resolve().parents[2]


def test_validate_idempotency_key_accepts_non_blank_key() -> None:
    validate_idempotency_key("review-action-001")


def test_validate_idempotency_key_rejects_blank_key() -> None:
    with pytest.raises(ValueError, match=IDEMPOTENCY_KEY_REQUIRED_MESSAGE):
        validate_idempotency_key("  ")


def test_api_idempotency_boundary_gate_passes_current_repository() -> None:
    module = _load_api_idempotency_boundary_gate()

    assert module.validate_api_idempotency_boundary(ROOT) == []


def test_api_idempotency_boundary_gate_blocks_optional_openapi_header() -> None:
    module = _load_api_idempotency_boundary_gate()
    method, path = module.REQUIRED_OPENAPI_IDEMPOTENCY_OPERATIONS[0]
    spec = {
        "paths": {
            path: {
                method: {
                    "parameters": [
                        {
                            "name": "Idempotency-Key",
                            "in": "header",
                            "required": False,
                            "schema": {"type": "string", "default": ""},
                        }
                    ]
                }
            }
        }
    }

    errors = module.validate_openapi_idempotency_headers(spec)

    assert errors == [
        f"{method.upper()} {path}: Idempotency-Key OpenAPI header must be required",
        f"{method.upper()} {path}: Idempotency-Key OpenAPI header must not publish a default value",
        "POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions: "
        "missing OpenAPI operation",
        "POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate: "
        "missing OpenAPI operation",
        "POST /api/v1/idea-candidates/{candidateId}/review-actions: missing OpenAPI operation",
        "POST /api/v1/idea-candidates/{candidateId}/feedback: missing OpenAPI operation",
        "POST /api/v1/idea-candidates/{candidateId}/conversion-intents: missing OpenAPI operation",
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions: "
        "missing OpenAPI operation",
        "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes: missing OpenAPI operation",
        "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs: "
        "missing OpenAPI operation",
        "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions: "
        "missing OpenAPI operation",
        "POST /api/v1/outbox-delivery/run-once: missing OpenAPI operation",
    ]


def test_openapi_idempotency_marker_tolerates_malformed_schema_shapes() -> None:
    schemas = [
        {},
        {"paths": []},
        {"paths": {"/api/v1/idea-signals/high-cash/evaluate-and-persist": None}},
        {"paths": {"/api/v1/idea-signals/high-cash/evaluate-and-persist": {"post": []}}},
        {
            "paths": {
                "/api/v1/idea-signals/high-cash/evaluate-and-persist": {"post": {"parameters": {}}}
            }
        },
        {
            "paths": {
                "/api/v1/idea-signals/high-cash/evaluate-and-persist": {
                    "post": {"parameters": [None]}
                }
            }
        },
    ]

    for schema in schemas:
        assert mark_required_idempotency_openapi_headers(schema) is schema


def test_api_idempotency_boundary_gate_blocks_route_local_validator(tmp_path: Path) -> None:
    module = _load_api_idempotency_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "idempotency.py").write_text(
        "def validate_idempotency_key(value: str) -> None:\n    pass\n",
        encoding="utf-8",
    )
    route_path = api_dir / "review_workflow.py"
    route_path.write_text(
        "def _validate_idempotency_key(value: str) -> None:\n    pass\n",
        encoding="utf-8",
    )

    errors = module.validate_api_idempotency_boundary(tmp_path)

    assert errors == [
        "src/app/api/review_workflow.py:1: API routes must use "
        "`app.api.idempotency.validate_idempotency_key` instead of defining "
        "`_validate_idempotency_key` locally"
    ]


def _load_api_idempotency_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_idempotency_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("api_idempotency_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
