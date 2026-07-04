from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from app.api.problem_details import (
    invalid_request_metadata,
    invalid_request_problem,
    merged_problem_response_metadata,
    permission_denied_problem,
    problem_details_response,
    service_unavailable_metadata,
)
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


WORKFLOW_OPERATIONS = (
    ("post", "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/review-actions", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/feedback", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/conversion-intents", (400, 403, 404, 409)),
    ("post", "/api/v1/conversion-intents/{conversionIntentId}/outcomes", (400, 403, 404, 409)),
    (
        "post",
        "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        (400, 403, 404, 409),
    ),
)


def test_problem_details_metadata_includes_product_safe_example() -> None:
    metadata = invalid_request_metadata(
        detail="Correct the lifecycle transition request and retry."
    )

    example = metadata[400]["content"]["application/json"]["example"]

    assert example == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Correct the lifecycle transition request and retry.",
    }


def test_service_unavailable_metadata_includes_product_safe_example() -> None:
    metadata = service_unavailable_metadata(
        code="downstream_realization_unavailable",
        title="Downstream realization unavailable",
        detail="The downstream realization adapter foundation is not configured.",
        description="Downstream realization adapters are not configured.",
    )

    example = metadata[503]["content"]["application/json"]["example"]

    assert example == {
        "type": "about:blank",
        "status": 503,
        "code": "downstream_realization_unavailable",
        "title": "Downstream realization unavailable",
        "detail": "The downstream realization adapter foundation is not configured.",
    }


def test_merged_problem_response_metadata_publishes_named_examples() -> None:
    metadata = merged_problem_response_metadata(
        status_code=503,
        description="Service is not write-ready.",
        responses=(
            service_unavailable_metadata(
                code="durable_repository_not_configured",
                title="Durable repository not configured",
                detail="Configure the durable repository before retrying.",
                description="Durable repository is not configured.",
            ),
            service_unavailable_metadata(
                code="downstream_realization_not_configured",
                title="Downstream realization not configured",
                detail="Configure the downstream adapter before retrying.",
                description="Downstream adapter is not configured.",
            ),
        ),
    )

    examples = metadata[503]["content"]["application/json"]["examples"]

    assert sorted(examples) == [
        "downstream_realization_not_configured",
        "durable_repository_not_configured",
    ]
    assert examples["downstream_realization_not_configured"]["value"]["status"] == 503


def test_permission_denied_problem_response_is_product_safe() -> None:
    response = permission_denied_problem("The caller is not permitted to record idea reviews.")

    assert response.status_code == 403
    assert b"permission_denied" in response.body
    assert b"The caller is not permitted to record idea reviews." in response.body


def test_invalid_request_problem_response_is_product_safe() -> None:
    response = invalid_request_problem("Correct the review workflow request and retry.")

    assert response.status_code == 400
    assert b"invalid_request" in response.body
    assert b"Correct the review workflow request and retry." in response.body


def test_problem_details_response_is_product_safe() -> None:
    response = problem_details_response(
        status_code=409,
        code="idempotency_conflict",
        title="Idempotency conflict",
        detail="The idempotency key was already used with a different request payload.",
    )

    assert response.status_code == 409
    assert b"idempotency_conflict" in response.body
    assert b"different request payload" in response.body


def test_workflow_openapi_error_responses_have_problem_details_examples() -> None:
    openapi = app.openapi()

    for method, path, status_codes in WORKFLOW_OPERATIONS:
        responses = openapi["paths"][path][method]["responses"]
        for status_code in status_codes:
            response = responses[str(status_code)]
            assert response["content"]["application/json"]["example"]["status"] == status_code
            assert response["content"]["application/json"]["example"]["type"] == "about:blank"
            assert response["content"]["application/json"]["example"]["code"]
            assert response["content"]["application/json"]["example"]["detail"]


def test_all_openapi_problem_details_responses_have_examples() -> None:
    openapi = app.openapi()
    missing: list[str] = []

    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            for status_code, response in operation.get("responses", {}).items():
                content = response.get("content", {}).get("application/json", {})
                schema_ref = content.get("schema", {}).get("$ref", "")
                if not schema_ref.endswith("/ProblemDetails"):
                    continue
                if "example" not in content and "examples" not in content:
                    missing.append(f"{method.upper()} {path} {status_code}")

    assert missing == []


def test_downstream_submission_openapi_problem_codes_match_runtime_contract() -> None:
    openapi = app.openapi()
    conversion_responses = openapi["paths"][
        "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"
    ]["post"]["responses"]
    report_responses = openapi["paths"][
        "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"
    ]["post"]["responses"]

    assert _problem_codes(conversion_responses["404"]) == {
        "downstream_realization_resource_not_found"
    }
    assert _problem_codes(report_responses["404"]) == {"downstream_realization_resource_not_found"}
    assert _problem_codes(conversion_responses["409"]) == {
        "idempotency_conflict",
        "unsupported_downstream_realization_target",
    }
    assert _problem_codes(report_responses["409"]) == {"idempotency_conflict"}
    assert _problem_codes(conversion_responses["503"]) == {
        "downstream_realization_not_configured",
        "durable_repository_not_configured",
        "durable_repository_unavailable",
    }
    assert _problem_codes(report_responses["503"]) == {
        "downstream_realization_not_configured",
        "durable_repository_not_configured",
        "durable_repository_unavailable",
    }
    stale_codes = {
        "conversion_intent_not_found",
        "report_evidence_pack_not_found",
        "unsupported_downstream_target",
        "downstream_realization_unavailable",
    }
    actual_codes = set().union(
        *(_problem_codes(response) for response in conversion_responses.values()),
        *(_problem_codes(response) for response in report_responses.values()),
    )
    assert stale_codes.isdisjoint(actual_codes)


def test_api_problem_details_boundary_gate_passes_current_repository() -> None:
    module = _load_api_problem_details_boundary_gate()

    assert module.validate_api_problem_details_boundary() == []


def test_api_problem_details_boundary_gate_blocks_direct_app_errors_import(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_api_problem_details_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    route_path = api_dir / "unsafe_route.py"
    route_path.write_text(
        "from app.errors import problem_response\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "API_DIR", api_dir)
    monkeypatch.setattr(module, "ALLOWED_DIRECT_ERROR_IMPORTS", {api_dir / "problem_details.py"})

    assert module.validate_api_problem_details_boundary() == [
        "src/app/api/unsafe_route.py:1: import problem_response through "
        "app.api.problem_details, not app.errors"
    ]


def test_api_problem_details_boundary_gate_blocks_entrypoint_app_errors_import(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_api_problem_details_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    main_path = tmp_path / "src" / "app" / "main.py"
    main_path.parent.mkdir(parents=True, exist_ok=True)
    main_path.write_text(
        "from app.errors import problem_response\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "API_DIR", api_dir)
    monkeypatch.setattr(module, "API_ENTRYPOINTS", (main_path,))
    monkeypatch.setattr(module, "ALLOWED_DIRECT_ERROR_IMPORTS", {api_dir / "problem_details.py"})

    assert module.validate_api_problem_details_boundary() == [
        "src/app/main.py:1: import problem_response through app.api.problem_details, not app.errors"
    ]


def _load_api_problem_details_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_problem_details_boundary_gate.py"
    spec = importlib.util.spec_from_file_location(
        "api_problem_details_boundary_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _problem_codes(response: dict[str, Any]) -> set[str]:
    media = response.get("content", {}).get("application/json", {})
    schema_ref = media.get("schema", {}).get("$ref", "")
    if not schema_ref.endswith("/ProblemDetails"):
        return set()
    if "example" in media:
        return {str(media["example"]["code"])}
    return {
        str(example_metadata["value"]["code"])
        for example_metadata in media.get("examples", {}).values()
    }
