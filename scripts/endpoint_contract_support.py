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
