from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_postgres_disaster_recovery_drill import (  # noqa: E402
    DEFAULT_OUTPUT_PATH,
    validate_restored_database,
)
from app.domain.disaster_recovery import RestoreValidationStatus  # noqa: E402


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware UTC")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a provider-restored Lotus Idea PostgreSQL database"
    )
    parser.add_argument("--backup-identifier", required=True)
    parser.add_argument("--backup-source", required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--backup-format", required=True)
    parser.add_argument("--backup-artifact-sha256", required=True)
    parser.add_argument("--pitr-proof", action="store_true")
    parser.add_argument("--backup-created-at-utc", type=_parse_utc, required=True)
    parser.add_argument("--incident-cutoff-utc", type=_parse_utc, required=True)
    parser.add_argument("--recovery-point-utc", type=_parse_utc, required=True)
    parser.add_argument("--restore-started-at-utc", type=_parse_utc, required=True)
    parser.add_argument("--restore-completed-at-utc", type=_parse_utc, required=True)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        evidence = validate_restored_database(
            backup_identifier=args.backup_identifier,
            backup_source=args.backup_source,
            operator_id=args.operator_id,
            correlation_id=args.correlation_id,
            backup_format=args.backup_format,
            backup_artifact_sha256=args.backup_artifact_sha256,
            pitr_proof=args.pitr_proof,
            backup_created_at_utc=args.backup_created_at_utc,
            incident_cutoff_utc=args.incident_cutoff_utc,
            recovery_point_utc=args.recovery_point_utc,
            restore_started_at_utc=args.restore_started_at_utc,
            restore_completed_at_utc=args.restore_completed_at_utc,
            output_path=args.output_path,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(f"PostgreSQL restored-database validation failed: {type(exc).__name__}")
        return 1
    print(f"PostgreSQL restored-database validation {evidence.status.value}")
    return 0 if evidence.status is RestoreValidationStatus.PASSED else 1


if __name__ == "__main__":
    sys.exit(main())
