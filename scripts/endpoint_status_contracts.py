from __future__ import annotations

import re
from typing import Any

from endpoint_contract_support import json_object_examples, openapi_success_object_examples


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
        for example in json_object_examples(endpoint.get("response_examples"))
    ):
        errors.append(
            f"{operation}: implemented_not_certified response_examples must preserve "
            "not-certified and no-promotion posture"
        )

    if openapi_spec is not None:
        if not any(
            _is_truthful_uncertified_posture(example)
            for example in openapi_success_object_examples(openapi_spec, operation)
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
            f"{operation}: implemented_not_certified endpoint must declare certification_blockers"
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


def _is_truthful_uncertified_posture(payload: dict[str, Any]) -> bool:
    return (
        payload.get("certificationStatus") == "not_certified"
        and payload.get("supportedFeaturePromoted") is False
    )
