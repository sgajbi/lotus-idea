from __future__ import annotations

import json
from typing import Any


def openapi_operation(
    openapi_spec: dict[str, Any],
    operation: tuple[str, str],
) -> dict[str, Any] | None:
    method, path = operation
    path_item = openapi_spec.get("paths", {}).get(path)
    if not isinstance(path_item, dict):
        return None
    operation_schema = path_item.get(method.lower())
    return operation_schema if isinstance(operation_schema, dict) else None


def openapi_success_object_examples(
    openapi_spec: dict[str, Any],
    operation: tuple[str, str],
) -> tuple[dict[str, Any], ...]:
    operation_schema = openapi_operation(openapi_spec, operation)
    if operation_schema is None:
        return ()
    responses = operation_schema.get("responses")
    if not isinstance(responses, dict):
        return ()

    candidates: list[Any] = []
    for status_code, response in responses.items():
        if not str(status_code).startswith("2") or not isinstance(response, dict):
            continue
        media = response.get("content", {}).get("application/json", {})
        if not isinstance(media, dict):
            continue
        if isinstance(media.get("example"), dict):
            candidates.append(media["example"])
        examples = media.get("examples")
        if isinstance(examples, dict):
            candidates.extend(
                metadata.get("value")
                for metadata in examples.values()
                if isinstance(metadata, dict)
            )
    return tuple(example for example in candidates if isinstance(example, dict))


def json_object_examples(examples: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(examples, list):
        return ()
    parsed: list[dict[str, Any]] = []
    for example in examples:
        if not isinstance(example, str) or not example.lstrip().startswith("{"):
            continue
        try:
            payload = json.loads(example)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            parsed.append(payload)
    return tuple(parsed)


def validate_named_success_contract(
    *,
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None,
    operation: tuple[str, str],
    expected: dict[str, dict[str, Any]],
    workflow_name: str,
    required_test_evidence: tuple[tuple[str, str], ...],
) -> list[str]:
    endpoint_operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if endpoint_operation != operation:
        return []

    errors: list[str] = []
    if json_object_examples(endpoint.get("response_examples")) != tuple(expected.values()):
        errors.append(
            f"{operation}: response_examples must exactly match every code-owned {workflow_name} "
            "success mode"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    for test_reference, evidence_description in required_test_evidence:
        if test_reference not in test_evidence:
            errors.append(f"{operation}: test_evidence must cite the {evidence_description}")

    if openapi_spec is not None:
        operation_schema = openapi_operation(openapi_spec, operation)
        media = (
            operation_schema.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            if operation_schema is not None
            else {}
        )
        examples = media.get("examples", {}) if isinstance(media, dict) else {}
        published = {
            str(name): metadata.get("value")
            for name, metadata in examples.items()
            if isinstance(metadata, dict)
        }
        if published != expected:
            errors.append(
                f"{operation}: OpenAPI 200 examples must exactly match every named "
                f"code-owned {workflow_name} success mode"
            )

    return errors


__all__ = [
    "json_object_examples",
    "openapi_operation",
    "openapi_success_object_examples",
    "validate_named_success_contract",
]
