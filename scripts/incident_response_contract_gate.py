# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

CONTRACT_PATH = Path("contracts/operations/lotus-idea-incident-response.v1.json")

REQUIRED_SEVERITY_IDS = {"sev1", "sev2", "sev3", "sev4"}
REQUIRED_FLOW = (
    "detect",
    "acknowledge",
    "triage",
    "assess_impact",
    "contain",
    "communicate",
    "recover",
    "verify",
    "document",
    "problem_review",
    "improve_controls",
)
REQUIRED_ROLE_IDS = {
    "incident_commander",
    "lotus_idea_service_owner",
    "platform_runtime_on_call",
    "database_on_call",
    "security_privacy_reviewer",
    "downstream_owner",
}
REQUIRED_SOURCE_TRUTH_KEYS = {
    "contract",
    "contract_gate",
    "unit_tests",
    "incident_runbook",
    "service_operations_runbook",
    "service_slo_capacity_doc",
    "operator_workflows_runbook",
    "postgres_disaster_recovery_runbook",
    "operations_wiki",
    "incident_response_wiki",
    "rfc_slice_15",
    "rfc_slice_18",
}
REQUIRED_EVIDENCE_POLICY_KEYS = {
    "allowed_identifiers",
    "prohibited_content",
    "evidence_storage",
    "github_tracking_required",
    "credential_rotation_decision_required",
    "evidence_preservation_required",
}
REQUIRED_PROBLEM_QUESTIONS = {
    "why_did_it_happen",
    "why_was_it_not_prevented",
    "why_was_it_not_detected_earlier",
    "did_runbook_work",
    "what_evidence_was_missing",
    "what_permanent_fix_is_needed",
    "what_gate_test_alert_or_runbook_should_change",
}
REQUIRED_ACTION_FAMILIES = {
    "add_or_harden_test",
    "add_or_tune_alert",
    "improve_dashboard_or_diagnostic",
    "improve_runbook_or_wiki",
    "update_contract_or_gate",
    "fix_dependency_timeout_retry_or_recovery",
    "update_context_skill_or_automation_when_repeatable",
}
REQUIRED_NON_PROOF_BOUNDARIES = {
    "This contract is not production on-call staffing certification.",
    "This contract is not protected-environment incident drill evidence.",
    "This contract is not customer-communication approval.",
    "This contract is not legal, privacy, suitability, execution, report rendering, or archive authority.",
    "This contract is not authentication or authorization implementation.",
    "This contract is not deployment or production certification.",
    "This contract is not data-mesh certification.",
    "This contract is not Gateway or Workbench proof.",
    "This contract is not supported-feature promotion.",
}
REQUIRED_DOC_FRAGMENTS = {
    "incident_runbook": (
        "Severity Model",
        "Escalation And Roles",
        "Source-Safe Evidence",
        "Communication Policy",
        "Post-Incident Problem Management",
        "not production on-call staffing certification",
    ),
    "service_operations_runbook": (
        "Incident Response Operating Model",
        "make incident-response-contract-gate",
    ),
    "operations_wiki": (
        "Incident response is declared",
        "Incident Response",
    ),
    "incident_response_wiki": (
        "Severity Model",
        "Post-Incident Problem Management",
        "not production on-call staffing certification",
    ),
}


def _load_contract(repository_root: Path, contract_path: Path) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("incident response contract must be a JSON object")
    return payload


def validate_incident_response_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    payload = _load_contract(repository_root, contract_path)
    return validate_incident_response_contract_payload(payload, repository_root=repository_root)


def validate_incident_response_contract_payload(
    payload: dict[str, Any], *, repository_root: Path = ROOT
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_header(payload))
    errors.extend(_validate_source_of_truth(payload, repository_root=repository_root))
    errors.extend(_validate_severity_classes(payload))
    errors.extend(_validate_response_flow(payload))
    errors.extend(_validate_escalation_roles(payload))
    errors.extend(_validate_source_safe_evidence_policy(payload))
    errors.extend(_validate_communication_policy(payload))
    errors.extend(_validate_problem_management(payload))
    errors.extend(_validate_non_proof_boundaries(payload))
    errors.extend(_validate_documentation_links(payload, repository_root=repository_root))
    return sorted(errors)


def _validate_header(payload: dict[str, Any]) -> list[str]:
    expected = {
        "contract_id": "lotus-idea-incident-response",
        "contract_version": "1.0.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_internal_foundation",
        "production_incident_certification_status": "not_certified",
        "supported_feature_promoted": False,
    }
    return [
        f"incident response contract {key} must be {value!r}"
        for key, value in expected.items()
        if payload.get(key) != value
    ]


def _validate_source_of_truth(payload: dict[str, Any], *, repository_root: Path) -> list[str]:
    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, dict):
        return ["incident response contract source_of_truth must be an object"]

    errors: list[str] = []
    missing = sorted(REQUIRED_SOURCE_TRUTH_KEYS - set(source_of_truth))
    if missing:
        errors.append(
            "incident response contract source_of_truth missing keys: " + ", ".join(missing)
        )
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str):
            errors.append(f"incident response contract source_of_truth.{key} must be a string path")
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"incident response contract source_of_truth.{key} path must stay relative"
            )
            continue
        if not (repository_root / path).exists():
            errors.append(f"incident response contract source_of_truth.{key} path missing")
    return errors


def _validate_severity_classes(payload: dict[str, Any]) -> list[str]:
    severities = payload.get("severity_classes")
    if not isinstance(severities, list):
        return ["incident response contract severity_classes must be a list"]
    errors: list[str] = []
    observed: set[str] = set()
    for index, severity in enumerate(severities):
        if not isinstance(severity, dict):
            errors.append(f"severity_classes[{index}] must be an object")
            continue
        severity_id = severity.get("severity_id")
        if not isinstance(severity_id, str) or not severity_id:
            errors.append(f"severity_classes[{index}].severity_id is required")
            continue
        observed.add(severity_id)
        for text_key in ("name", "business_impact", "escalation_owner"):
            if not isinstance(severity.get(text_key), str) or not severity[text_key].strip():
                errors.append(f"{severity_id}: {text_key} is required")
        for numeric_key in ("initial_response_target_minutes", "update_cadence_minutes"):
            if not isinstance(severity.get(numeric_key), int) or severity[numeric_key] <= 0:
                errors.append(f"{severity_id}: {numeric_key} must be a positive integer")
        for boolean_key in ("communication_required", "promotion_freeze_required"):
            if not isinstance(severity.get(boolean_key), bool):
                errors.append(f"{severity_id}: {boolean_key} must be a boolean")
    errors.extend(_required_id_errors("severity_classes", observed, REQUIRED_SEVERITY_IDS))
    return errors


def _validate_response_flow(payload: dict[str, Any]) -> list[str]:
    flow = payload.get("incident_response_flow")
    if flow != list(REQUIRED_FLOW):
        return [
            "incident response contract incident_response_flow must match governed "
            + " -> ".join(REQUIRED_FLOW)
        ]
    return []


def _validate_escalation_roles(payload: dict[str, Any]) -> list[str]:
    roles = payload.get("escalation_roles")
    if not isinstance(roles, list):
        return ["incident response contract escalation_roles must be a list"]
    errors: list[str] = []
    observed: set[str] = set()
    for index, role in enumerate(roles):
        if not isinstance(role, dict):
            errors.append(f"escalation_roles[{index}] must be an object")
            continue
        role_id = role.get("role_id")
        if not isinstance(role_id, str) or not role_id:
            errors.append(f"escalation_roles[{index}].role_id is required")
            continue
        observed.add(role_id)
        for key in ("owner_group", "responsibility", "escalation_condition"):
            if not isinstance(role.get(key), str) or not role[key].strip():
                errors.append(f"{role_id}: {key} is required")
    errors.extend(_required_id_errors("escalation_roles", observed, REQUIRED_ROLE_IDS))
    return errors


def _validate_source_safe_evidence_policy(payload: dict[str, Any]) -> list[str]:
    policy = payload.get("source_safe_evidence_policy")
    if not isinstance(policy, dict):
        return ["incident response contract source_safe_evidence_policy must be an object"]
    errors: list[str] = []
    missing = sorted(REQUIRED_EVIDENCE_POLICY_KEYS - set(policy))
    if missing:
        errors.append(
            "incident response contract source_safe_evidence_policy missing keys: "
            + ", ".join(missing)
        )
    for list_key in ("allowed_identifiers", "prohibited_content"):
        value = policy.get(list_key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            errors.append(
                f"incident response contract source_safe_evidence_policy.{list_key} must be a non-empty string list"
            )
    for bool_key in (
        "github_tracking_required",
        "credential_rotation_decision_required",
        "evidence_preservation_required",
    ):
        if policy.get(bool_key) is not True:
            errors.append(
                f"incident response contract source_safe_evidence_policy.{bool_key} must be true"
            )
    prohibited = set(policy.get("prohibited_content") or [])
    for required in ("secret", "DSN", "authorization header", "raw source payload"):
        if required not in prohibited:
            errors.append(f"incident response evidence policy must prohibit {required}")
    return errors


def _validate_communication_policy(payload: dict[str, Any]) -> list[str]:
    policy = payload.get("communication_policy")
    if not isinstance(policy, dict):
        return ["incident response contract communication_policy must be an object"]
    errors: list[str] = []
    for key in (
        "current_severity_required",
        "impact_statement_required",
        "next_update_time_required",
        "mitigation_status_required",
        "speculative_root_cause_prohibited",
    ):
        if policy.get(key) is not True:
            errors.append(f"incident response contract communication_policy.{key} must be true")
    boundary = policy.get("customer_communication_boundary")
    if not isinstance(boundary, str) or "customer-communications owner" not in boundary:
        errors.append(
            "incident response contract communication_policy.customer_communication_boundary "
            "must preserve external communication ownership"
        )
    return errors


def _validate_problem_management(payload: dict[str, Any]) -> list[str]:
    problem = payload.get("post_incident_problem_management")
    if not isinstance(problem, dict):
        return ["incident response contract post_incident_problem_management must be an object"]
    errors: list[str] = []
    for key in ("github_tracking_required", "action_owner_required", "due_date_required"):
        if problem.get(key) is not True:
            errors.append(
                f"incident response contract post_incident_problem_management.{key} must be true"
            )
    errors.extend(
        _required_list_values(
            owner="incident response problem questions",
            values=problem.get("required_questions"),
            required=REQUIRED_PROBLEM_QUESTIONS,
        )
    )
    errors.extend(
        _required_list_values(
            owner="incident response action families",
            values=problem.get("required_action_families"),
            required=REQUIRED_ACTION_FAMILIES,
        )
    )
    return errors


def _validate_non_proof_boundaries(payload: dict[str, Any]) -> list[str]:
    return _required_list_values(
        owner="incident response non-proof boundaries",
        values=payload.get("non_proof_boundaries"),
        required=REQUIRED_NON_PROOF_BOUNDARIES,
    )


def _validate_documentation_links(payload: dict[str, Any], *, repository_root: Path) -> list[str]:
    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, dict):
        return []
    errors: list[str] = []
    for key, fragments in REQUIRED_DOC_FRAGMENTS.items():
        value = source_of_truth.get(key)
        if not isinstance(value, str):
            continue
        path = repository_root / value
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                errors.append(f"{value}: missing required incident response fragment {fragment!r}")
    return errors


def _required_id_errors(owner: str, observed: set[str], required: set[str]) -> list[str]:
    errors: list[str] = []
    missing = sorted(required - observed)
    extra = sorted(observed - required)
    if missing:
        errors.append(f"incident response contract missing {owner}: " + ", ".join(missing))
    if extra:
        errors.append(
            f"incident response contract contains unsupported {owner}: " + ", ".join(extra)
        )
    return errors


def _required_list_values(*, owner: str, values: Any, required: set[str]) -> list[str]:
    if not isinstance(values, list):
        return [f"{owner} must be a list"]
    observed = {item for item in values if isinstance(item, str)}
    missing = sorted(required - observed)
    if missing:
        return [f"{owner} missing required values: " + "; ".join(missing)]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the lotus-idea incident response operating model contract."
    )
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_incident_response_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Incident response contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
