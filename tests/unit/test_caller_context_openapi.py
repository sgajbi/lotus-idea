from __future__ import annotations

from typing import Any, cast

from app.api.caller_context_openapi import (
    CALLER_CONTEXT_EXTENSION,
    PROBLEM_MEDIA_TYPES,
    PROTECTED_OPERATION_REQUIREMENTS,
    CallerContextOpenApiRequirement,
    _apply_operation_requirement,
    apply_caller_context_openapi_contract,
)
from app.main import app


def _operation(method: str, path: str) -> dict[str, Any]:
    schema = app.openapi()
    operation = schema["paths"][path][method.lower()]
    return cast(dict[str, Any], operation)


def _header_descriptions(operation: dict[str, Any]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        if parameter.get("in") != "header":
            continue
        name = parameter.get("name")
        if not isinstance(name, str):
            continue
        description = parameter.get("description", "")
        descriptions[name] = description if isinstance(description, str) else ""
    return descriptions


def test_signal_evaluation_openapi_publishes_caller_context_security() -> None:
    operation = _operation("POST", "/api/v1/idea-signals/high-cash/evaluate")

    assert operation["security"] == [{"LotusCallerContext": []}]
    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.signal.evaluate"]
    assert caller_context["requiredRoles"] == ["advisor"]
    assert "privileged X-Caller-* headers" in caller_context["trustedCallerContextProvenance"]
    headers = _header_descriptions(operation)
    assert headers["X-Caller-Capabilities"]
    assert headers["X-Lotus-Trusted-Caller-Context"]


def test_operator_readiness_openapi_publishes_caller_context_security() -> None:
    operation = _operation("GET", "/api/v1/implementation-proof/readiness")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.implementation-proof.readiness.read"]
    assert caller_context["requiredRoles"] == ["operator"]


def test_outbox_run_openapi_publishes_caller_context_security() -> None:
    operation = _operation("POST", "/api/v1/outbox-delivery/run-once")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.outbox-delivery.run"]
    assert caller_context["requiredRoles"] == ["operator"]


def test_advisor_queue_openapi_publishes_required_advisor_role() -> None:
    operation = _operation("GET", "/api/v1/review-queues/advisor")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.review.queue.read"]
    assert caller_context["requiredRoles"] == ["advisor"]


def test_candidate_detail_openapi_publishes_required_reader_roles() -> None:
    operation = _operation("GET", "/api/v1/idea-candidates/{candidateId}")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.candidate.detail.read"]
    assert caller_context["requiredRoles"] == ["advisor", "operator"]


def test_every_protected_operation_publishes_caller_boundary_problem_contracts() -> None:
    schema = app.openapi()

    for requirement in PROTECTED_OPERATION_REQUIREMENTS:
        operation = schema["paths"][requirement.path][requirement.method.lower()]
        for status_code, code in (("400", "invalid_request"), ("403", "permission_denied")):
            response = operation["responses"][status_code]
            for media_type in PROBLEM_MEDIA_TYPES:
                media = response["content"][media_type]
                examples = media.get("examples", {})
                assert examples[f"caller_context_{code}"]["value"]["code"] == code


def test_every_operation_with_caller_headers_is_registered_as_protected() -> None:
    schema = app.openapi()
    registered = {
        (requirement.method.lower(), requirement.path)
        for requirement in PROTECTED_OPERATION_REQUIREMENTS
    }
    operations_with_caller_headers: set[tuple[str, str]] = set()
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            header_names = {
                parameter.get("name")
                for parameter in operation.get("parameters", [])
                if isinstance(parameter, dict) and parameter.get("in") == "header"
            }
            if "X-Caller-Capabilities" in header_names:
                operations_with_caller_headers.add((method, path))

    assert operations_with_caller_headers == registered


def test_caller_context_openapi_contract_ignores_malformed_schema_sections() -> None:
    schema: dict[str, Any] = {
        "paths": {
            "/api/v1/idea-signals/high-cash/evaluate": "not-a-path-item",
            "/api/v1/review-queues/advisor": {"get": "not-an-operation"},
            "/unprotected": {"get": {"parameters": []}},
        }
    }

    assert apply_caller_context_openapi_contract(schema) is schema
    assert schema["paths"]["/unprotected"]["get"] == {"parameters": []}
    assert apply_caller_context_openapi_contract({"paths": []}) == {
        "components": {
            "securitySchemes": {
                "LotusCallerContext": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Caller-Capabilities",
                    "description": (
                        "Lotus caller-context capabilities propagated by trusted ingress. "
                        "Each protected operation publishes its required capability in "
                        "x-lotus-caller-context."
                    ),
                },
                "LotusTrustedCallerContext": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Lotus-Trusted-Caller-Context",
                    "description": (
                        "Trusted-ingress provenance marker required in demo, staging, and "
                        "production profiles when privileged X-Caller-* headers are present."
                    ),
                },
            }
        },
        "paths": [],
    }


def test_caller_context_openapi_contract_handles_sparse_parameters_and_alternatives() -> None:
    operation: dict[str, Any] = {
        "parameters": ["not-a-parameter", {"in": "query", "name": "limit"}]
    }
    _apply_operation_requirement(
        operation,
        CallerContextOpenApiRequirement(
            method="GET",
            path="/synthetic",
            required_capabilities=("idea.synthetic.read",),
            alternative_roles=("operator",),
        ),
    )

    caller_context = cast(dict[str, Any], operation[CALLER_CONTEXT_EXTENSION])
    assert caller_context["requiredCapabilities"] == ["idea.synthetic.read"]
    assert caller_context["alternativeRoles"] == ["operator"]

    schema: dict[str, Any] = {
        "paths": {
            "/api/v1/idea-signals/high-cash/evaluate": {
                "post": {
                    "parameters": "not-a-list",
                }
            }
        }
    }

    decorated = apply_caller_context_openapi_contract(schema)
    decorated_operation = cast(
        dict[str, Any],
        cast(dict[str, Any], decorated["paths"])["/api/v1/idea-signals/high-cash/evaluate"],
    )
    decorated_post = cast(dict[str, Any], decorated_operation["post"])
    decorated_context = cast(dict[str, Any], decorated_post[CALLER_CONTEXT_EXTENSION])

    assert decorated_context["requiredCapabilities"] == ["idea.signal.evaluate"]
