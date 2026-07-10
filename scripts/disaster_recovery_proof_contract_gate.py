from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/lotus-idea-postgres-disaster-recovery.v1.json"
DEFAULT_RESTORE_EVIDENCE = Path("output/disaster-recovery/postgres-restore-evidence.json")
DEFAULT_RESUME_EVIDENCE = Path("output/disaster-recovery/postgres-resume-evidence.json")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SECRET_PATTERNS = (
    re.compile(r"postgres(?:ql)?://", re.IGNORECASE),
    re.compile(r"(?:password|passwd|secret|token)\s*[=:]\s*[^\s]+", re.IGNORECASE),
)


def validate_disaster_recovery_proof(
    *,
    restore_evidence_path: Path = DEFAULT_RESTORE_EVIDENCE,
    resume_evidence_path: Path = DEFAULT_RESUME_EVIDENCE,
) -> list[str]:
    try:
        contract = _load_json(CONTRACT_PATH)
        restore = _load_json(_resolve(restore_evidence_path))
        resume = _load_json(_resolve(resume_evidence_path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"disaster recovery proof is unreadable: {exc}"]
    errors = _validate_restore(contract, restore)
    errors.extend(_validate_resume(restore, resume))
    errors.extend(_validate_source_safe(restore, "restore"))
    errors.extend(_validate_source_safe(resume, "resume"))
    return sorted(errors)


def _validate_restore(contract: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "evidence_version": "1.0.0",
        "validation_mode": "real_restore_validation",
        "status": "passed",
        "real_restored_backup": True,
        "synthetic_smoke": False,
        "source_safe": True,
        "supported_feature_promoted": False,
        "certification_status": "not_certified",
    }
    errors.extend(_expected_values(evidence, expected, "restore evidence"))
    if evidence.get("failed_checks") != []:
        errors.append("disaster recovery restore evidence must have no failed checks")
    for field in (
        "backup_artifact_sha256",
        "database_identity_sha256",
        "migration_bundle_sha256",
    ):
        if not SHA256.fullmatch(str(evidence.get(field, ""))):
            errors.append(f"disaster recovery restore {field} must be SHA-256")
    if evidence.get("pitr_proof") is False and evidence.get("backup_format") != (
        "postgres-custom-logical"
    ):
        errors.append("non-PITR restore evidence must identify the logical backup format")

    objectives = contract["recovery_objectives"]
    if _number(evidence, "actual_rpo_seconds") > int(objectives["rpo_minutes"]) * 60:
        errors.append("disaster recovery restore evidence breached RPO")
    if _number(evidence, "actual_rto_seconds") > int(objectives["rto_minutes"]) * 60:
        errors.append("disaster recovery restore evidence breached RTO")
    errors.extend(_validate_timestamps(evidence))

    restore_policy = contract["restore_verification"]
    expected_tables = set(restore_policy["owned_tables"])
    row_counts = evidence.get("restored_table_row_counts")
    hashes = evidence.get("restored_table_content_sha256")
    if not isinstance(row_counts, dict) or set(row_counts) != expected_tables:
        errors.append("disaster recovery restore row-count table inventory drifted")
    if not isinstance(hashes, dict) or set(hashes) != expected_tables:
        errors.append("disaster recovery restore hash table inventory drifted")
    elif any(not SHA256.fullmatch(str(digest)) for digest in hashes.values()):
        errors.append("disaster recovery restored table hashes must be SHA-256")
    if isinstance(row_counts, dict):
        for table in restore_policy["required_non_empty_tables"]:
            if not isinstance(row_counts.get(table), int) or row_counts[table] <= 0:
                errors.append(f"disaster recovery representative table is empty: {table}")
    return errors


def _validate_resume(restore: dict[str, Any], resume: dict[str, Any]) -> list[str]:
    expected = {
        "evidence_version": "1.0.0",
        "status": "passed",
        "candidate_replay_decision": "replayed",
        "outbox_recovery_replay_decision": "replayed",
        "stale_lease_finalize_decision": "lease_conflict",
        "no_duplicate_or_mutation": True,
        "source_safe": True,
        "supported_feature_promoted": False,
        "certification_status": "not_certified",
    }
    errors = _expected_values(resume, expected, "resume evidence")
    decisions = resume.get("downstream_claim_decisions")
    if decisions != {
        "conversion_intent": "reconciliation_required",
        "report_evidence_pack": "reconciliation_required",
    }:
        errors.append("disaster recovery downstream resume decisions drifted")
    before = resume.get("table_content_sha256_before")
    after = resume.get("table_content_sha256_after")
    if before != after:
        errors.append("disaster recovery resume mutated restored state")
    if before != restore.get("restored_table_content_sha256"):
        errors.append("disaster recovery resume did not start from validated restore hashes")
    return errors


def _validate_timestamps(evidence: dict[str, Any]) -> list[str]:
    names = (
        "backup_created_at_utc",
        "recovery_point_utc",
        "incident_cutoff_utc",
        "restore_started_at_utc",
        "restore_completed_at_utc",
        "service_ready_at_utc",
    )
    try:
        values = [_parse_utc(evidence[name]) for name in names]
    except (KeyError, TypeError, ValueError) as exc:
        return [f"disaster recovery restore timestamp is invalid: {exc}"]
    if values != sorted(values):
        return ["disaster recovery restore timestamps must be chronologically ordered"]
    return []


def _validate_source_safe(payload: dict[str, Any], label: str) -> list[str]:
    serialized = json.dumps(payload, sort_keys=True)
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        return [f"disaster recovery {label} evidence contains a DSN or secret"]
    return []


def _expected_values(payload: dict[str, Any], expected: dict[str, Any], label: str) -> list[str]:
    return [
        f"disaster recovery {label} {key} must be {value!r}"
        for key, value in expected.items()
        if payload.get(key) != value
    ]


def _number(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field} must be a non-negative number")
    return float(value)


def _parse_utc(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp must be timezone-aware UTC")
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PostgreSQL restore proof evidence")
    parser.add_argument("--restore-evidence", type=Path, default=DEFAULT_RESTORE_EVIDENCE)
    parser.add_argument("--resume-evidence", type=Path, default=DEFAULT_RESUME_EVIDENCE)
    args = parser.parse_args()
    try:
        errors = validate_disaster_recovery_proof(
            restore_evidence_path=args.restore_evidence,
            resume_evidence_path=args.resume_evidence,
        )
    except ValueError as exc:
        errors = [f"disaster recovery proof is invalid: {exc}"]
    if errors:
        print("\n".join(errors))
        return 1
    print("PostgreSQL disaster recovery proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
