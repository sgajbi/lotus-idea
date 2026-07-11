from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.disaster_recovery import ValidateRestoredDatabase  # noqa: E402
from app.domain.disaster_recovery import (  # noqa: E402
    DisasterRecoveryPolicy,
    RestoreDrillEvidence,
    RestoreDrillRequest,
    RestoreValidationStatus,
)
from app.infrastructure.postgres_backup_restore import (  # noqa: E402
    PostgresBackupRestoreCommandError,
    PostgresLogicalBackupRestore,
)
from app.infrastructure.postgres_disaster_recovery import (  # noqa: E402
    PostgresRestoredDatabaseInspector,
)
from scripts.disaster_recovery_evidence_io import (  # noqa: E402
    write_dataclass_evidence_atomic,
)

CONTRACT_PATH = ROOT / "contracts/operations/lotus-idea-postgres-disaster-recovery.v1.json"
MIGRATIONS_PATH = ROOT / "migrations"
SOURCE_DATABASE_URL_ENV = "LOTUS_IDEA_DR_SOURCE_DATABASE_URL"
TARGET_DATABASE_URL_ENV = "LOTUS_IDEA_DR_TARGET_DATABASE_URL"
DEFAULT_OUTPUT_PATH = ROOT / "output/disaster-recovery/postgres-restore-evidence.json"


def run_disaster_recovery_drill(
    *,
    backup_identifier: str,
    backup_source: str,
    operator_id: str,
    correlation_id: str,
    incident_cutoff_utc: datetime | None = None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    source_database_url: str | None = None,
    target_database_url: str | None = None,
    backup_restore: Any | None = None,
    inspector_factory: Any = PostgresRestoredDatabaseInspector,
    now: Any | None = None,
) -> RestoreDrillEvidence:
    source_url = source_database_url or os.getenv(SOURCE_DATABASE_URL_ENV, "").strip()
    target_url = target_database_url or os.getenv(TARGET_DATABASE_URL_ENV, "").strip()
    if not source_url or not target_url:
        raise ValueError(f"{SOURCE_DATABASE_URL_ENV} and {TARGET_DATABASE_URL_ENV} are required")
    runner = backup_restore or PostgresLogicalBackupRestore()
    restore = runner.execute(
        source_database_url=source_url,
        target_database_url=target_url,
    )
    cutoff = incident_cutoff_utc or restore.recovery_point_utc
    return validate_restored_database(
        backup_identifier=backup_identifier,
        backup_source=backup_source,
        operator_id=operator_id,
        correlation_id=correlation_id,
        backup_format=restore.backup_format,
        backup_artifact_sha256=restore.backup_artifact_sha256,
        pitr_proof=restore.pitr_proof,
        backup_created_at_utc=restore.backup_created_at_utc,
        incident_cutoff_utc=cutoff,
        recovery_point_utc=restore.recovery_point_utc,
        restore_started_at_utc=restore.restore_started_at_utc,
        restore_completed_at_utc=restore.restore_completed_at_utc,
        output_path=output_path,
        target_database_url=target_url,
        inspector_factory=inspector_factory,
        now=now,
    )


def validate_restored_database(
    *,
    backup_identifier: str,
    backup_source: str,
    operator_id: str,
    correlation_id: str,
    backup_format: str,
    backup_artifact_sha256: str,
    pitr_proof: bool,
    backup_created_at_utc: datetime,
    incident_cutoff_utc: datetime,
    recovery_point_utc: datetime,
    restore_started_at_utc: datetime,
    restore_completed_at_utc: datetime,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    target_database_url: str | None = None,
    inspector_factory: Any = PostgresRestoredDatabaseInspector,
    now: Any | None = None,
) -> RestoreDrillEvidence:
    target_url = target_database_url or os.getenv(TARGET_DATABASE_URL_ENV, "").strip()
    if not target_url:
        raise ValueError(f"{TARGET_DATABASE_URL_ENV} is required")
    contract = _load_contract()
    policy = _policy_from_contract(contract)
    request = RestoreDrillRequest(
        backup_identifier=backup_identifier,
        backup_source=backup_source,
        operator_id=operator_id,
        correlation_id=correlation_id,
        backup_format=backup_format,
        backup_artifact_sha256=backup_artifact_sha256,
        pitr_proof=pitr_proof,
        migration_bundle_sha256=_migration_bundle_sha256(),
        latest_migration=_latest_migration(),
        backup_created_at_utc=backup_created_at_utc,
        incident_cutoff_utc=incident_cutoff_utc,
        recovery_point_utc=recovery_point_utc,
        restore_started_at_utc=restore_started_at_utc,
        restore_completed_at_utc=restore_completed_at_utc,
    )
    use_case = ValidateRestoredDatabase(
        inspector_factory(target_url),
        policy,
        now=now,
    )
    evidence = use_case.execute(request)
    write_dataclass_evidence_atomic(output_path, evidence)
    return evidence


def _load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("disaster recovery contract must be an object")
    return payload


def _policy_from_contract(contract: dict[str, Any]) -> DisasterRecoveryPolicy:
    objectives = contract["recovery_objectives"]
    restore = contract["restore_verification"]
    return DisasterRecoveryPolicy(
        rpo_minutes=int(objectives["rpo_minutes"]),
        rto_minutes=int(objectives["rto_minutes"]),
        owned_tables=frozenset(restore["owned_tables"]),
        allowed_unvalidated_constraints=frozenset(restore["allowed_unvalidated_constraints"]),
        required_non_empty_tables=frozenset(restore["required_non_empty_tables"]),
    )


def _migration_bundle_sha256() -> str:
    digest = hashlib.sha256()
    for path in _forward_migrations():
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _latest_migration() -> str:
    migrations = _forward_migrations()
    if not migrations:
        raise ValueError("no forward migrations found")
    return migrations[-1].stem


def _forward_migrations() -> list[Path]:
    return [
        path
        for path in sorted(MIGRATIONS_PATH.glob("[0-9][0-9][0-9]_*.sql"))
        if not path.name.endswith(".rollback.sql")
    ]


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware UTC")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore and validate a real Lotus Idea PostgreSQL logical backup"
    )
    parser.add_argument("--backup-identifier", required=True)
    parser.add_argument("--backup-source", required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--incident-cutoff-utc", type=_parse_utc)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        evidence = run_disaster_recovery_drill(
            backup_identifier=args.backup_identifier,
            backup_source=args.backup_source,
            operator_id=args.operator_id,
            correlation_id=args.correlation_id,
            incident_cutoff_utc=args.incident_cutoff_utc,
            output_path=args.output_path,
        )
    except PostgresBackupRestoreCommandError as exc:
        print(f"PostgreSQL disaster recovery drill failed: {exc}")
        return 1
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(f"PostgreSQL disaster recovery drill failed: {type(exc).__name__}")
        return 1
    print(f"PostgreSQL disaster recovery drill {evidence.status.value}")
    return 0 if evidence.status is RestoreValidationStatus.PASSED else 1


if __name__ == "__main__":
    sys.exit(main())
