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

from app.observability import (  # noqa: E402
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_METRIC_LABELS,
    IdeaOperation,
    OperationOutcome,
)

CONTRACT_PATH = Path("contracts/observability/lotus-idea-operator-workflows-operations.v1.json")
EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
REQUIRED_DASHBOARD_CONTROLS = {
    "source-ingestion-readiness-and-run-once-posture",
    "outbox-delivery-backlog-and-recovery-posture",
    "downstream-realization-readiness-and-submission-posture",
    "runtime-trust-and-implementation-proof-readiness-posture",
}
REQUIRED_ALERT_CANDIDATES = {
    "source-ingestion-readiness-blocked",
    "outbox-delivery-readiness-blocked",
    "downstream-realization-readiness-blocked",
    "implementation-proof-readiness-blocked",
}
REQUIRED_NON_PROOF_BOUNDARIES = {
    "This contract is not live source-ingestion certification.",
    "This contract is not external broker runtime certification.",
    "This contract is not downstream execution outcome authority.",
    "This contract is not data-mesh certification.",
    "This contract is not Gateway or Workbench proof.",
    "This contract is not supported-feature promotion.",
}


def _load_contract(repository_root: Path, contract_path: Path) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("operator workflows operations contract must be a JSON object")
    return payload


def validate_operator_workflows_operations_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    payload = _load_contract(repository_root, contract_path)
    return validate_operator_workflows_operations_contract_payload(
        payload,
        repository_root=repository_root,
    )


def validate_operator_workflows_operations_contract_payload(
    payload: dict[str, Any],
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_header(payload))
    errors.extend(_validate_source_of_truth(payload, repository_root=repository_root))
    errors.extend(_validate_dashboard_controls(payload))
    errors.extend(_validate_alert_candidates(payload))
    errors.extend(_validate_non_proof_boundaries(payload))
    return sorted(errors)


def _validate_header(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "contract_id": "lotus-idea-operator-workflows-operations",
        "contract_version": "1.0.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_internal_foundation",
        "supportability_status": "not_certified",
        "supported_feature_promoted": False,
        "dashboard_certified": True,
        "alert_certified": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"operator workflows operations contract {key} must be {value!r}")
    return errors


def _validate_source_of_truth(
    payload: dict[str, Any],
    *,
    repository_root: Path,
) -> list[str]:
    source_of_truth = payload.get("source_of_truth")
    required_keys = {
        "operation_metric_contract",
        "contract_gate",
        "proof_contract_gate",
        "dashboard",
        "alert_rules",
        "operator_runbook",
        "operations_doc",
        "service_operations_runbook",
        "operations_wiki",
        "source_ingestion_source",
        "outbox_delivery_source",
        "downstream_realization_source",
        "runtime_trust_source",
        "implementation_proof_source",
        "rfc_slice_15",
        "rfc_slice_17",
    }
    if not isinstance(source_of_truth, dict):
        return ["operator workflows operations contract source_of_truth must be an object"]

    errors: list[str] = []
    missing = sorted(required_keys - set(source_of_truth))
    if missing:
        errors.append(
            "operator workflows operations contract source_of_truth missing keys: "
            + ", ".join(missing)
        )
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str):
            errors.append(
                f"operator workflows operations contract source_of_truth.{key} "
                "must be a string path"
            )
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"operator workflows operations contract source_of_truth.{key} "
                "path must stay relative"
            )
            continue
        if not (repository_root / path).exists():
            errors.append(
                f"operator workflows operations contract source_of_truth.{key} path missing"
            )
    return errors


def _validate_dashboard_controls(payload: dict[str, Any]) -> list[str]:
    controls = payload.get("operator_dashboard_controls")
    if not isinstance(controls, list):
        return ["operator workflows operations contract dashboard controls must be a list"]
    errors: list[str] = []
    observed: set[str] = set()
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            errors.append(f"dashboard controls[{index}] must be an object")
            continue
        control_id = control.get("control_id")
        if not isinstance(control_id, str) or not control_id.strip():
            errors.append(f"dashboard controls[{index}].control_id is required")
            continue
        observed.add(control_id)
        if not control.get("operator_question"):
            errors.append(f"{control_id}: operator_question is required")
        if control.get("implemented_metric_family") != EXPECTED_METRIC_NAME:
            errors.append(f"{control_id}: implemented_metric_family must be {EXPECTED_METRIC_NAME}")
        if control.get("certification_status") != "certified":
            errors.append(f"{control_id}: certification_status must be certified")
        endpoints = control.get("required_endpoints")
        if not isinstance(endpoints, list) or not endpoints:
            errors.append(f"{control_id}: required_endpoints must be a non-empty list")
        errors.extend(_validate_operations(control_id, control.get("required_operations")))
        errors.extend(_validate_labels(control_id, control.get("required_labels")))
    return _validate_expected_ids(
        errors,
        observed,
        REQUIRED_DASHBOARD_CONTROLS,
        "dashboard controls",
    )


def _validate_alert_candidates(payload: dict[str, Any]) -> list[str]:
    alerts = payload.get("operator_alert_candidates")
    if not isinstance(alerts, list):
        return ["operator workflows operations contract alert candidates must be a list"]
    errors: list[str] = []
    observed: set[str] = set()
    valid_outcomes = {outcome.value for outcome in OperationOutcome}
    for index, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            errors.append(f"alert candidates[{index}] must be an object")
            continue
        alert_id = alert.get("alert_id")
        if not isinstance(alert_id, str) or not alert_id.strip():
            errors.append(f"alert candidates[{index}].alert_id is required")
            continue
        observed.add(alert_id)
        if alert.get("implemented_metric_family") != EXPECTED_METRIC_NAME:
            errors.append(f"{alert_id}: implemented_metric_family must be {EXPECTED_METRIC_NAME}")
        if alert.get("certification_status") != "certified":
            errors.append(f"{alert_id}: certification_status must be certified")
        if not alert.get("operator_response"):
            errors.append(f"{alert_id}: operator_response is required")
        errors.extend(_validate_operations(alert_id, alert.get("required_operations")))
        outcomes = alert.get("required_outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            errors.append(f"{alert_id}: required_outcomes must be a non-empty list")
        elif any(outcome not in valid_outcomes for outcome in outcomes):
            errors.append(f"{alert_id}: required_outcomes must use code-owned outcomes")
    return _validate_expected_ids(
        errors,
        observed,
        REQUIRED_ALERT_CANDIDATES,
        "alert candidates",
    )


def _validate_expected_ids(
    errors: list[str],
    observed: set[str],
    required: set[str],
    section_name: str,
) -> list[str]:
    missing = sorted(required - observed)
    extra = sorted(observed - required)
    if missing:
        errors.append(
            f"operator workflows operations contract missing {section_name}: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            f"operator workflows operations contract contains unsupported {section_name}: "
            + ", ".join(extra)
        )
    return errors


def _validate_operations(owner: str, operations: Any) -> list[str]:
    if not isinstance(operations, list) or not operations:
        return [f"{owner}: required_operations must be a non-empty list"]
    valid_operations = {operation.value for operation in IdeaOperation}
    invalid = sorted(operation for operation in operations if operation not in valid_operations)
    if invalid:
        return [
            f"{owner}: required_operations contain unsupported operations: {', '.join(invalid)}"
        ]
    return []


def _validate_labels(owner: str, labels: Any) -> list[str]:
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


def _validate_non_proof_boundaries(payload: dict[str, Any]) -> list[str]:
    boundaries = payload.get("non_proof_boundaries")
    if not isinstance(boundaries, list):
        return ["operator workflows operations contract non_proof_boundaries must be a list"]
    missing = sorted(
        REQUIRED_NON_PROOF_BOUNDARIES - {item for item in boundaries if isinstance(item, str)}
    )
    if missing:
        return [
            "operator workflows operations contract missing non-proof boundaries: "
            + "; ".join(missing)
        ]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the lotus-idea operator workflows operations contract."
    )
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_operator_workflows_operations_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Operator workflows operations contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
