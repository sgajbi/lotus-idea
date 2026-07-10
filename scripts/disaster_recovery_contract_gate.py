from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("contracts/operations/lotus-idea-postgres-disaster-recovery.v1.json")
MIGRATIONS_PATH = Path("migrations")

EXPECTED_HEADER = {
    "contract_id": "lotus-idea-postgres-disaster-recovery",
    "contract_version": "1.0.0",
    "repository": "lotus-idea",
    "data_owner": "lotus-idea",
    "certification_status": "not_certified",
    "supported_feature_promoted": False,
}
EXPECTED_OBJECTIVES = {
    "rpo_minutes": 15,
    "rto_minutes": 60,
    "rpo_measurement": "incident_cutoff_utc minus recovery_point_utc",
    "rto_measurement": "authorized_restore_start_utc through validated_service_ready_utc",
}
EXPECTED_BACKUP_POLICY = {
    "strategy": "physical_base_backup_plus_continuous_wal_archiving",
    "base_backup_frequency_hours": 24,
    "continuous_wal_archiving_required": True,
    "point_in_time_recovery_required": True,
    "logical_dump_is_pitr_proof": False,
    "operational_retention_days": 35,
    "encryption_at_rest_required": True,
    "encryption_in_transit_required": True,
    "customer_managed_key_supported": True,
    "credential_rotation_required": True,
    "secrets_in_arguments_or_evidence_forbidden": True,
}
EXPECTED_ACCESS_POLICY = {
    "restore_region_policy": "same_approved_jurisdiction",
    "cross_region_restore_requires_approval": True,
    "least_privilege_restore_role_required": True,
    "dual_authorization_for_production_cutover": True,
    "break_glass_access_audited": True,
}
EXPECTED_CADENCE = {
    "restore_verification_cadence": "weekly",
    "full_dr_exercise_cadence": "quarterly",
}
REQUIRED_INVARIANTS = {
    "migration_history_and_schema_compatibility",
    "required_primary_foreign_key_unique_and_check_constraints",
    "required_operational_indexes",
    "cross_table_referential_integrity",
    "candidate_evidence_and_audit_lineage_integrity",
    "idempotency_key_replay_and_conflict_integrity",
    "outbox_status_lease_retry_dead_letter_and_publication_integrity",
    "downstream_submission_status_lease_and_realization_integrity",
    "ai_explanation_candidate_lineage_integrity",
    "resume_without_duplicate_outbox_or_downstream_publication",
}
REQUIRED_EVIDENCE_FLAGS = {
    "real_restored_backup_required": True,
    "synthetic_smoke_is_certification_proof": False,
    "backup_identifier_required": True,
    "backup_artifact_sha256_required": True,
    "sanitized_source_identity_required": True,
    "schema_version_required": True,
    "backup_created_at_utc_required": True,
    "recovery_point_utc_required": True,
    "restore_started_at_utc_required": True,
    "service_ready_at_utc_required": True,
    "rpo_and_rto_measurements_required": True,
    "table_row_counts_and_source_safe_hashes_required": True,
    "invariant_results_required": True,
    "operator_and_correlation_identity_required": True,
    "signed_immutable_evidence_required": True,
    "alert_on_backup_age_restore_failure_or_rpo_breach": True,
}
REQUIRED_RESTORE_FLAGS = {
    "clean_target_instance_required": True,
    "source_and_target_must_differ": True,
    "post_migration_restore_required": True,
}
EXPECTED_ALLOWED_UNVALIDATED_CONSTRAINTS = {"ck_idea_candidate_record_state_policy_v1"}
EXPECTED_OPTIONAL_EMPTY_TABLES = {
    "idea_candidate_state_quarantine",
    "idea_conversion_outcome_quarantine",
}
CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(idea_[a-z0-9_]+)", re.IGNORECASE
)
SECRET_PATTERNS = (
    re.compile(r"postgres(?:ql)?://", re.IGNORECASE),
    re.compile(r"(?:password|passwd|secret|token)\s*[=:]\s*[^\s]+", re.IGNORECASE),
)


def validate_disaster_recovery_contract(
    *, repository_root: Path = ROOT, contract_path: Path = CONTRACT_PATH
) -> list[str]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"disaster recovery contract is unreadable: {exc}"]
    if not isinstance(payload, dict):
        return ["disaster recovery contract must be an object"]

    errors = _validate_expected_values(payload, EXPECTED_HEADER, "header")
    errors.extend(_validate_sources(payload, repository_root))
    errors.extend(
        _validate_expected_values(
            payload.get("recovery_objectives"), EXPECTED_OBJECTIVES, "recovery objectives"
        )
    )
    errors.extend(
        _validate_expected_values(
            payload.get("backup_and_pitr"), EXPECTED_BACKUP_POLICY, "backup policy"
        )
    )
    errors.extend(
        _validate_expected_values(
            payload.get("residency_and_access"), EXPECTED_ACCESS_POLICY, "access policy"
        )
    )
    errors.extend(
        _validate_expected_values(
            payload.get("operating_model"), EXPECTED_CADENCE, "operating cadence"
        )
    )
    errors.extend(_validate_restore_inventory(payload, repository_root))
    errors.extend(_validate_evidence(payload))
    errors.extend(_validate_no_embedded_secrets(payload))
    return sorted(errors)


def _validate_expected_values(value: Any, expected: dict[str, Any], section: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"disaster recovery {section} must be an object"]
    return [
        f"disaster recovery {section} {key} must be {expected_value!r}"
        for key, expected_value in expected.items()
        if value.get(key) != expected_value
    ]


def _validate_sources(payload: dict[str, Any], repository_root: Path) -> list[str]:
    sources = payload.get("source_of_truth")
    if not isinstance(sources, dict) or not sources:
        return ["disaster recovery source_of_truth must be a non-empty object"]
    errors: list[str] = []
    for name, value in sources.items():
        if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
            errors.append(f"disaster recovery source {name} must be a safe relative path")
        elif not (repository_root / value).exists():
            errors.append(f"disaster recovery source {name} is missing")
    return errors


def _migration_owned_tables(repository_root: Path) -> set[str]:
    tables: set[str] = set()
    for migration in sorted((repository_root / MIGRATIONS_PATH).glob("*.sql")):
        if migration.name.endswith(".rollback.sql"):
            continue
        tables.update(CREATE_TABLE_PATTERN.findall(migration.read_text(encoding="utf-8")))
    return tables


def _validate_restore_inventory(payload: dict[str, Any], repository_root: Path) -> list[str]:
    restore = payload.get("restore_verification")
    errors = _validate_expected_values(restore, REQUIRED_RESTORE_FLAGS, "restore verification")
    if not isinstance(restore, dict):
        return errors

    owned_tables = restore.get("owned_tables")
    if not isinstance(owned_tables, list) or not all(
        isinstance(table, str) for table in owned_tables
    ):
        errors.append("disaster recovery owned_tables must be a list of table names")
    else:
        declared = set(owned_tables)
        migrated = _migration_owned_tables(repository_root)
        if len(owned_tables) != len(declared):
            errors.append("disaster recovery owned_tables must not contain duplicates")
        if declared != migrated:
            errors.append(
                "disaster recovery owned_tables must exactly match idea tables declared by migrations"
            )

    invariants = restore.get("required_invariants")
    if not isinstance(invariants, list) or set(invariants) != REQUIRED_INVARIANTS:
        errors.append("disaster recovery required invariant inventory drifted")
    allowed_constraints = restore.get("allowed_unvalidated_constraints")
    if not isinstance(allowed_constraints, list) or set(allowed_constraints) != (
        EXPECTED_ALLOWED_UNVALIDATED_CONSTRAINTS
    ):
        errors.append("disaster recovery unvalidated constraint exception inventory drifted")
    required_non_empty = restore.get("required_non_empty_tables")
    expected_non_empty = _migration_owned_tables(repository_root).difference(
        EXPECTED_OPTIONAL_EMPTY_TABLES
    )
    if not isinstance(required_non_empty, list) or set(required_non_empty) != expected_non_empty:
        errors.append("disaster recovery representative-state table inventory drifted")
    return errors


def _validate_evidence(payload: dict[str, Any]) -> list[str]:
    errors = _validate_expected_values(
        payload.get("evidence_requirements"), REQUIRED_EVIDENCE_FLAGS, "evidence requirements"
    )
    blockers = payload.get("certification_blockers")
    if (
        not isinstance(blockers, list)
        or len(blockers) < 5
        or not all(isinstance(blocker, str) and blocker.strip() for blocker in blockers)
    ):
        errors.append("disaster recovery certification_blockers must name remaining proof")
    return errors


def _validate_no_embedded_secrets(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, sort_keys=True)
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        return ["disaster recovery contract must not embed credentials, DSNs, or secrets"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PostgreSQL disaster recovery contract")
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    errors = validate_disaster_recovery_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("PostgreSQL disaster recovery contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
