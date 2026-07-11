from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from scripts.migration_table_inventory import migration_owned_tables
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from migration_table_inventory import migration_owned_tables  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("contracts/operations/lotus-idea-data-lifecycle.v1.json")
MIGRATIONS_PATH = Path("migrations")

EXPECTED_HEADER = {
    "contract_id": "lotus-idea-data-lifecycle",
    "contract_version": "1.0.0",
    "repository": "lotus-idea",
    "data_owner": "lotus-idea",
    "certification_status": "not_certified",
    "supported_feature_promoted": False,
}
EXPECTED_AUTHORITIES = {
    "local_enforcement_owner": "lotus-idea",
    "retention_policy_approval_authority": "bank-records-and-privacy-governance",
    "legal_hold_decision_authority": "bank-legal-and-records-governance",
    "subject_erasure_decision_authority": "bank-privacy-governance",
    "report_policy_source_authority": "lotus-report",
    "archive_record_source_authority": "lotus-archive",
    "ai_provider_retention_source_authority": "lotus-ai",
    "idea_may_self_authorize_legal_hold_or_erasure": False,
}
EXPECTED_EXTERNAL_POLICIES = {
    "lotus-report:idea-evidence-retention:v1": (
        "lotus-idea:regulated-advisory-evidence:seven-year:v1"
    )
}
REQUIRED_CONTROL_FLAGS = {
    "unknown_policy_fails_closed": True,
    "missing_tenant_scope_fails_closed": True,
    "missing_authority_fails_closed": True,
    "legal_hold_precedes_expiry_erasure_and_purge": True,
    "exact_tenant_entitlement_required": True,
    "capability_and_role_required": True,
    "dual_authorization_required_for_release_erasure_and_purge": True,
    "idempotency_and_request_fingerprint_required": True,
    "dry_run_preview_required": True,
    "aggregate_lock_fences_concurrent_writes": True,
    "active_outbox_or_downstream_work_blocks_erasure": True,
    "bounded_batch_maximum": 100,
    "raw_sensitive_values_in_logs_metrics_or_evidence_forbidden": True,
    "cross_service_decision_reference_required": True,
}
REQUIRED_RECORD_FIELDS = {
    "table",
    "field_classification_profile_ref",
    "residency_policy_ref",
    "data_classes",
    "purpose",
    "policy_ref",
    "hold_behavior",
    "erasure_policy",
    "purge_policy",
}
REQUIRED_RESIDENCY_POLICY = "bank-approved-primary-and-dr-regions:v1"
POLICY_REF_PATTERN = re.compile(r"^[a-z0-9-]+:[a-z0-9-]+:[a-z0-9-]+:v[1-9][0-9]*$")
DURATION_PATTERN = re.compile(r"^P(?:[1-9][0-9]*Y|[1-9][0-9]*D)$")
SECRET_PATTERNS = (
    re.compile(r"postgres(?:ql)?://", re.IGNORECASE),
    re.compile(r"(?:password|passwd|secret|token)\s*[=:]\s*[^\s]+", re.IGNORECASE),
)


def validate_data_lifecycle_contract(
    *, repository_root: Path = ROOT, contract_path: Path = CONTRACT_PATH
) -> list[str]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"data lifecycle contract is unreadable: {exc}"]
    if not isinstance(payload, dict):
        return ["data lifecycle contract must be an object"]

    errors = _expected_values(payload, EXPECTED_HEADER, "header")
    errors.extend(_validate_sources(payload, repository_root))
    errors.extend(
        _expected_values(payload.get("authority_boundaries"), EXPECTED_AUTHORITIES, "authorities")
    )
    errors.extend(_validate_policies(payload))
    errors.extend(_validate_classification_and_residency(payload))
    errors.extend(_validate_record_inventory(payload, repository_root))
    errors.extend(
        _expected_values(payload.get("enforcement_controls"), REQUIRED_CONTROL_FLAGS, "controls")
    )
    errors.extend(_validate_remaining_proof(payload))
    errors.extend(_validate_no_embedded_secrets(payload))
    return sorted(errors)


def _expected_values(value: Any, expected: dict[str, Any], section: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"data lifecycle {section} must be an object"]
    return [
        f"data lifecycle {section} {key} must be {expected_value!r}"
        for key, expected_value in expected.items()
        if value.get(key) != expected_value
    ]


def _validate_sources(payload: dict[str, Any], repository_root: Path) -> list[str]:
    sources = payload.get("source_of_truth")
    if not isinstance(sources, dict) or not sources:
        return ["data lifecycle source_of_truth must be a non-empty object"]
    errors: list[str] = []
    for name, value in sources.items():
        if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
            errors.append(f"data lifecycle source {name} must be a safe relative path")
        elif not (repository_root / value).exists():
            errors.append(f"data lifecycle source {name} is missing")
    return errors


def _validate_policies(payload: dict[str, Any]) -> list[str]:
    policies = payload.get("retention_policies")
    if not isinstance(policies, list) or not policies:
        return ["data lifecycle retention_policies must be a non-empty list"]
    errors: list[str] = []
    policy_refs: list[str] = []
    for policy in policies:
        if not isinstance(policy, dict):
            errors.append("data lifecycle retention policy must be an object")
            continue
        policy_ref = policy.get("policy_ref")
        if not isinstance(policy_ref, str) or not POLICY_REF_PATTERN.fullmatch(policy_ref):
            errors.append("data lifecycle policy_ref must be a versioned source-safe reference")
        else:
            policy_refs.append(policy_ref)
        if not isinstance(policy.get("duration"), str) or not DURATION_PATTERN.fullmatch(
            policy["duration"]
        ):
            errors.append("data lifecycle policy duration must be a positive ISO year/day duration")
        if policy.get("automatic_physical_delete") is not False:
            errors.append("data lifecycle automatic physical delete must remain disabled")
        for key in ("start_event", "expiry_behavior"):
            if not isinstance(policy.get(key), str) or not policy[key].strip():
                errors.append(f"data lifecycle policy {key} is required")
    if len(policy_refs) != len(set(policy_refs)):
        errors.append("data lifecycle policy_ref values must be unique")
    external = payload.get("accepted_external_policy_refs")
    if external != EXPECTED_EXTERNAL_POLICIES:
        errors.append("data lifecycle accepted external policy references drifted")
    elif not set(external.values()).issubset(policy_refs):
        errors.append("data lifecycle external policy mapping must resolve to a local policy")
    return errors


def _validate_record_inventory(payload: dict[str, Any], repository_root: Path) -> list[str]:
    inventory = payload.get("record_inventory")
    if not isinstance(inventory, list):
        return ["data lifecycle record_inventory must be a list"]
    errors: list[str] = []
    tables: list[str] = []
    policy_refs = {
        policy.get("policy_ref")
        for policy in payload.get("retention_policies", [])
        if isinstance(policy, dict)
    }
    profile_refs = set(payload.get("field_classification_profiles", {}))
    for record in inventory:
        if not isinstance(record, dict):
            errors.append("data lifecycle record inventory entry must be an object")
            continue
        missing = REQUIRED_RECORD_FIELDS.difference(record)
        if missing:
            errors.append(
                "data lifecycle record inventory entry is missing: " + ", ".join(sorted(missing))
            )
            continue
        table = record["table"]
        if isinstance(table, str):
            tables.append(table)
        if record["policy_ref"] not in policy_refs:
            errors.append(f"data lifecycle table {table} references an unknown policy")
        if record["field_classification_profile_ref"] not in profile_refs:
            errors.append(
                f"data lifecycle table {table} references an unknown field classification profile"
            )
        if record["residency_policy_ref"] != REQUIRED_RESIDENCY_POLICY:
            errors.append(f"data lifecycle table {table} must declare governed residency")
        if not isinstance(record["data_classes"], list) or not record["data_classes"]:
            errors.append(f"data lifecycle table {table} must declare data classes")
        for key in ("purpose", "hold_behavior", "erasure_policy", "purge_policy"):
            if not isinstance(record[key], str) or not record[key].strip():
                errors.append(f"data lifecycle table {table} {key} is required")
    migrated = migration_owned_tables(repository_root, MIGRATIONS_PATH)
    if len(tables) != len(set(tables)):
        errors.append("data lifecycle record inventory must not contain duplicate tables")
    if set(tables) != migrated:
        errors.append("data lifecycle record inventory must exactly match migrated idea tables")
    return errors


def _validate_classification_and_residency(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    residency = payload.get("residency_policies")
    if not isinstance(residency, dict) or REQUIRED_RESIDENCY_POLICY not in residency:
        errors.append("data lifecycle governed residency policy is required")
    else:
        policy = residency[REQUIRED_RESIDENCY_POLICY]
        required = {
            "storage_boundary",
            "cross_region_replication",
            "cross_border_transfer_authority",
        }
        if not isinstance(policy, dict) or any(
            not isinstance(policy.get(key), str) or not policy[key].strip() for key in required
        ):
            errors.append("data lifecycle residency policy must define deployment boundaries")

    profiles = payload.get("field_classification_profiles")
    if not isinstance(profiles, dict) or not profiles:
        return [*errors, "data lifecycle field classification profiles are required"]
    for profile_ref, profile in profiles.items():
        if not isinstance(profile_ref, str) or not profile_ref.endswith(":v1"):
            errors.append("data lifecycle field classification profile must be versioned")
            continue
        if not isinstance(profile, dict):
            errors.append(f"data lifecycle classification profile {profile_ref} must be an object")
            continue
        rules = profile.get("rules")
        if (
            not isinstance(rules, dict)
            or not rules
            or any(
                not isinstance(pattern, str)
                or not pattern.strip()
                or not isinstance(classification, str)
                or not classification.strip()
                for pattern, classification in (rules.items() if isinstance(rules, dict) else ())
            )
        ):
            errors.append(f"data lifecycle classification profile {profile_ref} needs rules")
        fallback = profile.get("fallback_class")
        if not isinstance(fallback, str) or not fallback.strip():
            errors.append(f"data lifecycle classification profile {profile_ref} needs fallback")
    return errors


def _validate_remaining_proof(payload: dict[str, Any]) -> list[str]:
    research = payload.get("research_basis")
    blockers = payload.get("certification_blockers")
    errors: list[str] = []
    if not isinstance(research, list) or len(research) < 3:
        errors.append("data lifecycle research_basis must document governing rationale")
    if not isinstance(blockers, list) or len(blockers) < 5:
        errors.append("data lifecycle certification_blockers must name remaining proof")
    return errors


def _validate_no_embedded_secrets(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, sort_keys=True)
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        return ["data lifecycle contract must not embed credentials, DSNs, or secrets"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Idea data lifecycle contract")
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    errors = validate_data_lifecycle_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Data lifecycle contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
