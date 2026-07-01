from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.observability import (
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_METRIC_LABELS,
    IdeaOperation,
)


PayloadValidator = Callable[[dict[str, Any]], list[str]]
SourceOfTruthValidator = Callable[..., list[str]]
OperationsContractValidators = tuple[
    PayloadValidator,
    SourceOfTruthValidator,
    PayloadValidator,
    PayloadValidator,
    PayloadValidator,
]


def validate_operations_contract_payload(
    payload: dict[str, Any],
    *,
    repository_root: Path,
    validators: OperationsContractValidators,
) -> list[str]:
    (
        validate_header,
        validate_source_of_truth,
        validate_dashboard_controls,
        validate_alert_candidates,
        validate_non_proof_boundaries,
    ) = validators
    errors: list[str] = []
    errors.extend(validate_header(payload))
    errors.extend(validate_source_of_truth(payload, repository_root=repository_root))
    errors.extend(validate_dashboard_controls(payload))
    errors.extend(validate_alert_candidates(payload))
    errors.extend(validate_non_proof_boundaries(payload))
    return sorted(errors)


def validate_required_operations(owner: str, operations: Any) -> list[str]:
    if not isinstance(operations, list) or not operations:
        return [f"{owner}: required_operations must be a non-empty list"]
    valid_operations = {operation.value for operation in IdeaOperation}
    invalid = sorted(operation for operation in operations if operation not in valid_operations)
    if invalid:
        return [
            f"{owner}: required_operations contain unsupported operations: {', '.join(invalid)}"
        ]
    return []


def validate_required_labels(owner: str, labels: Any) -> list[str]:
    if not isinstance(labels, list) or not labels:
        return [f"{owner}: required_labels must be a non-empty list"]
    valid_labels = set(OPERATION_METRIC_LABELS)
    invalid = sorted(label for label in labels if label not in valid_labels)
    sensitive = sorted(
        label
        for label in labels
        if isinstance(label, str) and label in FORBIDDEN_OPERATION_FIELD_KEYS
    )
    errors: list[str] = []
    if invalid:
        errors.append(f"{owner}: required_labels contain unsupported labels: {', '.join(invalid)}")
    if sensitive:
        errors.append(f"{owner}: required_labels contain sensitive labels: {', '.join(sensitive)}")
    return errors
