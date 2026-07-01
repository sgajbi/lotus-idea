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

from app.observability import OperationOutcome  # noqa: E402

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


CONTRACT_PATH = Path("contracts/observability/lotus-idea-ai-model-risk-operations.v1.json")
EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
REQUIRED_DASHBOARD_CONTROLS = {
    "ai-explanation-readiness-posture",
    "ai-output-verifier-posture",
    "ai-lineage-durability-posture",
}
REQUIRED_ALERT_CANDIDATES = {
    "ai-explanation-unsupported-claim-block-rate",
    "ai-explanation-readiness-remains-blocked",
}
REQUIRED_NON_PROOF_BOUNDARIES = {
    "This contract is not lotus-ai runtime execution proof.",
    "This contract is not certified AI lineage-store proof.",
    "This contract is not Gateway or Workbench proof.",
    "This contract is not supported-feature promotion.",
}


def _load_contract(repository_root: Path, contract_path: Path) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("AI model-risk operations contract must be a JSON object")
    return payload


def validate_ai_model_risk_operations_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    payload = _load_contract(repository_root, contract_path)
    return validate_ai_model_risk_operations_contract_payload(
        payload,
        repository_root=repository_root,
    )


# fmt: off
def validate_ai_model_risk_operations_contract_payload(
    payload: dict[str, Any], *, repository_root: Path = ROOT
) -> list[str]:
    return validate_operations_contract_payload(payload, repository_root=repository_root, validators=OPERATIONS_CONTRACT_VALIDATORS)
# fmt: on


def _validate_header(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "contract_id": "lotus-idea-ai-model-risk-operations",
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
            errors.append(f"AI model-risk operations contract {key} must be {value!r}")
    return errors


def _validate_source_of_truth(
    payload: dict[str, Any],
    *,
    repository_root: Path,
) -> list[str]:
    source_of_truth = payload.get("source_of_truth")
    required_keys = {
        "ai_readiness_source",
        "ai_api_source",
        "operation_metric_contract",
        "contract_gate",
        "proof_contract_gate",
        "dashboard",
        "alert_rules",
        "model_risk_runbook",
        "operations_doc",
        "ai_governance_doc",
        "operations_runbook",
        "rfc_slice_09",
        "rfc_slice_15",
    }
    if not isinstance(source_of_truth, dict):
        return ["AI model-risk operations contract source_of_truth must be an object"]

    errors: list[str] = []
    missing = sorted(required_keys - set(source_of_truth))
    if missing:
        errors.append(
            "AI model-risk operations contract source_of_truth missing keys: " + ", ".join(missing)
        )
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str):
            errors.append(
                f"AI model-risk operations contract source_of_truth.{key} must be a string path"
            )
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"AI model-risk operations contract source_of_truth.{key} path must stay relative"
            )
            continue
        if not (repository_root / path).exists():
            errors.append(f"AI model-risk operations contract source_of_truth.{key} path missing")
    return errors


def _validate_dashboard_controls(payload: dict[str, Any]) -> list[str]:
    controls = payload.get("model_risk_dashboard_controls")
    if not isinstance(controls, list):
        return ["AI model-risk operations contract dashboard controls must be a list"]

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
        if not control.get("required_endpoint"):
            errors.append(f"{control_id}: required_endpoint is required")
        errors.extend(validate_required_operations(control_id, control.get("required_operations")))
        errors.extend(validate_required_labels(control_id, control.get("required_labels")))
    missing = sorted(REQUIRED_DASHBOARD_CONTROLS - observed)
    extra = sorted(observed - REQUIRED_DASHBOARD_CONTROLS)
    if missing:
        errors.append(
            "AI model-risk operations contract missing dashboard controls: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "AI model-risk operations contract contains unsupported dashboard controls: "
            + ", ".join(extra)
        )
    return errors


def _validate_alert_candidates(payload: dict[str, Any]) -> list[str]:
    alerts = payload.get("model_risk_alert_candidates")
    if not isinstance(alerts, list):
        return ["AI model-risk operations contract alert candidates must be a list"]

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
        errors.extend(validate_required_operations(alert_id, alert.get("required_operations")))
        outcomes = alert.get("required_outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            errors.append(f"{alert_id}: required_outcomes must be a non-empty list")
        elif any(outcome not in valid_outcomes for outcome in outcomes):
            errors.append(f"{alert_id}: required_outcomes must use code-owned outcomes")
    missing = sorted(REQUIRED_ALERT_CANDIDATES - observed)
    extra = sorted(observed - REQUIRED_ALERT_CANDIDATES)
    if missing:
        errors.append(
            "AI model-risk operations contract missing alert candidates: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "AI model-risk operations contract contains unsupported alert candidates: "
            + ", ".join(extra)
        )
    return errors


def _validate_non_proof_boundaries(payload: dict[str, Any]) -> list[str]:
    boundaries = payload.get("non_proof_boundaries")
    if not isinstance(boundaries, list):
        return ["AI model-risk operations contract non_proof_boundaries must be a list"]
    missing = sorted(
        REQUIRED_NON_PROOF_BOUNDARIES - {item for item in boundaries if isinstance(item, str)}
    )
    if missing:
        return [
            "AI model-risk operations contract missing non-proof boundaries: " + "; ".join(missing)
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
        description="Validate the lotus-idea AI model-risk operations contract."
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=CONTRACT_PATH,
        help="Repository-relative AI model-risk operations contract path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_ai_model_risk_operations_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("AI model-risk operations contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
