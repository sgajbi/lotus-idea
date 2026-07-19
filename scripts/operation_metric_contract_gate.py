# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.observability import (  # noqa: E402
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_EVENT_SOURCE_AUTHORITIES,
    OPERATION_METRIC_LABELS,
    IdeaOperation,
    OperationOutcome,
    OperationSupportability,
)


CONTRACT_PATH = Path("contracts/observability/lotus-idea-operation-metrics.v1.json")
EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
EXPECTED_METRIC_TYPE = "counter"


def _load_contract(repository_root: Path, contract_path: Path) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("operation metric contract must be a JSON object")
    return payload


def validate_operation_metric_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    payload = _load_contract(repository_root, contract_path)
    return validate_operation_metric_contract_payload(payload, repository_root=repository_root)


def validate_operation_metric_contract_payload(
    payload: dict[str, Any],
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_header(payload))
    errors.extend(_validate_source_of_truth(payload, repository_root=repository_root))
    errors.extend(_validate_metrics(payload))
    errors.extend(_validate_non_proof_boundaries(payload))
    return sorted(errors)


def _validate_header(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "contract_id": "lotus-idea-operation-metrics",
        "contract_version": "1.0.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_internal_foundation",
        "supportability_status": "not_certified",
        "supported_feature_promoted": False,
        "dashboard_certified": False,
        "alert_certified": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"operation metric contract {key} must be {value!r}")
    return errors


def _validate_source_of_truth(
    payload: dict[str, Any],
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    source_of_truth = payload.get("source_of_truth")
    required_keys = {
        "metric_source",
        "contract_gate",
        "operations_doc",
        "operations_runbook",
        "rfc_slice_15",
    }
    if not isinstance(source_of_truth, dict):
        return ["operation metric contract source_of_truth must be an object"]
    missing = sorted(required_keys - set(source_of_truth))
    if missing:
        errors.append(
            "operation metric contract source_of_truth missing keys: " + ", ".join(missing)
        )
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str):
            errors.append(f"operation metric contract source_of_truth.{key} must be a string path")
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"operation metric contract source_of_truth.{key} path must stay relative"
            )
            continue
        if not (repository_root / path).exists():
            errors.append(f"operation metric contract source_of_truth.{key} path missing")
    return errors


def _validate_metrics(payload: dict[str, Any]) -> list[str]:
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        return ["operation metric contract metrics must be a list"]
    if len(metrics) != 1:
        return ["operation metric contract must declare exactly one metric"]
    metric = metrics[0]
    if not isinstance(metric, dict):
        return ["operation metric contract metric entries must be objects"]

    errors: list[str] = []
    if metric.get("metric_name") != EXPECTED_METRIC_NAME:
        errors.append(f"operation metric name must be {EXPECTED_METRIC_NAME}")
    if metric.get("prometheus_type") != EXPECTED_METRIC_TYPE:
        errors.append(f"operation metric prometheus_type must be {EXPECTED_METRIC_TYPE}")
    if metric.get("description") != "Count of bounded lotus-idea business operation events.":
        errors.append("operation metric description must match code-owned counter help text")

    labels = metric.get("labels")
    if labels != list(OPERATION_METRIC_LABELS):
        errors.append(
            "operation metric labels must match code-owned OPERATION_METRIC_LABELS in order"
        )
    if isinstance(labels, list):
        leaked_labels = FORBIDDEN_OPERATION_FIELD_KEYS.intersection(
            label for label in labels if isinstance(label, str)
        )
        if leaked_labels:
            errors.append(
                "operation metric labels contain sensitive keys: "
                + ", ".join(sorted(leaked_labels))
            )

    source_authorities = metric.get("source_authorities")
    if source_authorities != list(OPERATION_EVENT_SOURCE_AUTHORITIES):
        errors.append(
            "operation metric source_authorities must match code-owned "
            "OPERATION_EVENT_SOURCE_AUTHORITIES in order"
        )

    outcomes = metric.get("outcomes")
    expected_outcomes = sorted(outcome.value for outcome in OperationOutcome)
    if not isinstance(outcomes, list) or sorted(outcomes) != expected_outcomes:
        errors.append("operation metric outcomes must match code-owned OperationOutcome values")

    operations = metric.get("operations")
    if not isinstance(operations, list):
        errors.append("operation metric operations must be a list")
    else:
        errors.extend(_validate_operations(operations))
    return errors


def _validate_operations(operations: list[Any]) -> list[str]:
    errors: list[str] = []
    expected_operations = {operation.value for operation in IdeaOperation}
    observed_operations: set[str] = set()
    supportability_values = {status.value for status in OperationSupportability}
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            errors.append(f"operation metric operations[{index}] must be an object")
            continue
        operation_name = operation.get("operation")
        if not isinstance(operation_name, str):
            errors.append(f"operation metric operations[{index}].operation must be a string")
            continue
        observed_operations.add(operation_name)
        if not operation.get("scope"):
            errors.append(f"{operation_name}: scope is required")
        source_authority = operation.get("source_authority")
        if source_authority not in OPERATION_EVENT_SOURCE_AUTHORITIES:
            errors.append(f"{operation_name}: source_authority is not a governed Lotus authority")
        supportability_status = operation.get("supportability_status")
        if supportability_status not in supportability_values:
            errors.append(f"{operation_name}: supportability_status is not code-owned vocabulary")
        if supportability_status == OperationSupportability.SUPPORTED.value:
            errors.append(f"{operation_name}: supported status is blocked until feature promotion")

    missing_operations = sorted(expected_operations - observed_operations)
    extra_operations = sorted(observed_operations - expected_operations)
    if missing_operations:
        errors.append(
            "operation metric contract missing operations: " + ", ".join(missing_operations)
        )
    if extra_operations:
        errors.append(
            "operation metric contract contains unsupported operations: "
            + ", ".join(extra_operations)
        )
    return errors


def _validate_non_proof_boundaries(payload: dict[str, Any]) -> list[str]:
    boundaries = payload.get("non_proof_boundaries")
    required = {
        "This contract is not dashboard certification.",
        "This contract is not alert certification.",
        "This contract is not data-mesh certification.",
        "This contract is not Gateway or Workbench proof.",
        "This contract is not supported-feature promotion.",
    }
    if not isinstance(boundaries, list):
        return ["operation metric contract non_proof_boundaries must be a list"]
    missing = sorted(required - {item for item in boundaries if isinstance(item, str)})
    if missing:
        return ["operation metric contract missing non-proof boundaries: " + "; ".join(missing)]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the lotus-idea operation metric contract."
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=CONTRACT_PATH,
        help="Repository-relative operation metric contract path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_operation_metric_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Operation metric contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
