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
    AGGREGATE_SOURCE_AUTHORITY,
    OPERATION_EVENT_SOURCE_AUTHORITIES,
    OperationOutcome,
    OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC,
    OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC,
    OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC,
    OUTBOX_DELIVERY_STATE_METRIC,
)

try:
    from scripts.operations_contract_validators import (  # noqa: E402
        validate_operations_contract_payload,
        validate_required_labels,
        validate_required_operations,
    )
except ModuleNotFoundError:
    from operations_contract_validators import (  # type: ignore[import-not-found,no-redef] # noqa: E402
        validate_operations_contract_payload,
        validate_required_labels,
        validate_required_operations,
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
    "This contract is not dashboard provisioning or query-execution proof.",
    "This contract is not alert-rule loading, evaluation, or delivery proof.",
    "This contract is not deployment or production certification.",
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


# fmt: off
def validate_operator_workflows_operations_contract_payload(
    payload: dict[str, Any], *, repository_root: Path = ROOT
) -> list[str]:
    errors = validate_operations_contract_payload(
        payload,
        repository_root=repository_root,
        validators=OPERATIONS_CONTRACT_VALIDATORS,
    )
    errors.extend(_validate_source_authority_policy(payload))
    return sorted(errors)
# fmt: on


def _validate_header(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "contract_id": "lotus-idea-operator-workflows-operations",
        "contract_version": "1.1.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_internal_foundation",
        "supportability_status": "not_certified",
        "supported_feature_promoted": False,
        "dashboard_source_contract_valid": True,
        "alert_rules_source_contract_valid": True,
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
        "outbox_supportability_contract",
        "outbox_supportability_contract_gate",
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
        if control.get("source_contract_status") != "valid":
            errors.append(f"{control_id}: source_contract_status must be valid")
        endpoints = control.get("required_endpoints")
        if not isinstance(endpoints, list) or not endpoints:
            errors.append(f"{control_id}: required_endpoints must be a non-empty list")
        errors.extend(validate_required_operations(control_id, control.get("required_operations")))
        errors.extend(validate_required_labels(control_id, control.get("required_labels")))
        if control_id == "outbox-delivery-backlog-and-recovery-posture":
            expected_metrics = [
                OUTBOX_DELIVERY_STATE_METRIC,
                OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC,
                OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC,
                OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC,
            ]
            if control.get("supportability_metric_families") != expected_metrics:
                errors.append(
                    f"{control_id}: supportability_metric_families must match code-owned metrics"
                )
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
        if alert.get("source_contract_status") != "valid":
            errors.append(f"{alert_id}: source_contract_status must be valid")
        if not alert.get("operator_response"):
            errors.append(f"{alert_id}: operator_response is required")
        errors.extend(validate_required_operations(alert_id, alert.get("required_operations")))
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


def _validate_source_authority_policy(payload: dict[str, Any]) -> list[str]:
    policy = payload.get("source_authority_policy")
    if not isinstance(policy, dict):
        return ["operator workflows operations contract source_authority_policy must be an object"]
    errors: list[str] = []
    if policy.get("label_source") != (
        "src/app/observability/logging.py::OPERATION_EVENT_SOURCE_AUTHORITIES"
    ):
        errors.append(
            "operator workflows operations contract source authority label source drifted"
        )
    if policy.get("aggregate_label") != AGGREGATE_SOURCE_AUTHORITY:
        errors.append("operator workflows operations contract aggregate source authority drifted")
    if policy.get("governed_labels") != list(OPERATION_EVENT_SOURCE_AUTHORITIES):
        errors.append(
            "operator workflows operations contract governed source authority labels "
            "must match code-owned OPERATION_EVENT_SOURCE_AUTHORITIES"
        )
    return errors


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


OPERATIONS_CONTRACT_VALIDATORS = (
    _validate_header,
    _validate_source_of_truth,
    _validate_dashboard_controls,
    _validate_alert_candidates,
    _validate_non_proof_boundaries,
)


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
