from __future__ import annotations

import json
import re
from typing import Any


IMPLEMENTED_NOT_CERTIFIED = "implemented_not_certified"
BLOCKER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_endpoint_status_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    if endpoint.get("certification_status") != IMPLEMENTED_NOT_CERTIFIED:
        return []

    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    errors = _validate_certification_blockers(operation, endpoint)
    if not any(
        _is_truthful_uncertified_posture(example)
        for example in _json_object_examples(endpoint.get("response_examples"))
    ):
        errors.append(
            f"{operation}: implemented_not_certified response_examples must preserve "
            "not-certified and no-promotion posture"
        )

    if openapi_spec is not None:
        operation_schema = _openapi_operation(openapi_spec, operation)
        if operation_schema is None or not any(
            _is_truthful_uncertified_posture(example)
            for example in _openapi_success_examples(operation_schema)
        ):
            errors.append(
                f"{operation}: OpenAPI success examples must preserve not-certified "
                "and no-promotion posture"
            )
    return errors


def _validate_certification_blockers(
    operation: tuple[str, str],
    endpoint: dict[str, Any],
) -> list[str]:
    blockers = endpoint.get("certification_blockers")
    if not isinstance(blockers, list) or not blockers:
        return [
            f"{operation}: implemented_not_certified endpoint must declare "
            "certification_blockers"
        ]
    errors: list[str] = []
    for index, blocker in enumerate(blockers):
        if not isinstance(blocker, str) or BLOCKER_PATTERN.fullmatch(blocker) is None:
            errors.append(
                f"{operation}: certification_blockers[{index}] must use snake_case vocabulary"
            )
    if len(blockers) != len(set(blockers)):
        errors.append(f"{operation}: certification_blockers must not contain duplicates")
    return errors


def _openapi_operation(
    openapi_spec: dict[str, Any],
    operation: tuple[str, str],
) -> dict[str, Any] | None:
    method, path = operation
    path_item = openapi_spec.get("paths", {}).get(path)
    if not isinstance(path_item, dict):
        return None
    operation_schema = path_item.get(method.lower())
    return operation_schema if isinstance(operation_schema, dict) else None


def _openapi_success_examples(operation_schema: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    media = (
        operation_schema.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
    )
    if not isinstance(media, dict):
        return ()
    candidates: list[Any] = []
    if isinstance(media.get("example"), dict):
        candidates.append(media["example"])
    examples = media.get("examples")
    if isinstance(examples, dict):
        candidates.extend(
            metadata.get("value") for metadata in examples.values() if isinstance(metadata, dict)
        )
    return tuple(example for example in candidates if isinstance(example, dict))


def _json_object_examples(examples: Any) -> tuple[dict[str, Any], ...]:
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


def _is_truthful_uncertified_posture(payload: dict[str, Any]) -> bool:
    return (
        payload.get("certificationStatus") == "not_certified"
        and payload.get("supportedFeaturePromoted") is False
    )
