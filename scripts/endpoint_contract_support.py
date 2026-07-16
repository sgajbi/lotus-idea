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
