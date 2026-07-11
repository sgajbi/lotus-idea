from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

import psycopg

from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
)
from app.infrastructure.postgres_capacity_stress import PostgresCapacityStressAdapter


CONFIRMATION = "SATURATE_DEDICATED_LOTUS_IDEA_POSTGRES"
DATABASE_URL_ENV = "LOTUS_IDEA_DATABASE_URL"
DEFAULT_OUTPUT = Path("output/observability/postgres-capacity-threshold-proof.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded PostgreSQL capacity threshold and recovery proof."
    )
    parser.add_argument("--environment-profile", required=True, choices=("test",))
    parser.add_argument("--expected-database-name", required=True)
    parser.add_argument("--maximum-target-connections", type=int, required=True)
    parser.add_argument("--maximum-load-connections", type=int, default=100)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    stress_adapter: PostgresCapacityStressAdapter | None = None
    try:
        if args.confirmation != CONFIRMATION:
            raise ValueError(f"confirmation must exactly equal {CONFIRMATION}")
        database_url = os.getenv(DATABASE_URL_ENV, "").strip()
        if not database_url:
            raise ValueError(f"{DATABASE_URL_ENV} is required")
        stress_adapter = PostgresCapacityStressAdapter(
            database_url=database_url,
            expected_database_name=args.expected_database_name,
            maximum_target_connections=args.maximum_target_connections,
        )
        artifact = execute_postgres_capacity_threshold_proof(
            stress_port=stress_adapter,
            environment_profile=args.environment_profile,
            generated_at_utc=datetime.now(UTC),
            commit_sha=args.commit_sha,
            branch=args.branch,
            run_id=args.run_id,
            maximum_load_connections=args.maximum_load_connections,
        )
        _write_json_atomic(args.output, artifact)
        return 0
    except (OSError, ValueError, psycopg.Error) as exc:
        print(f"PostgreSQL capacity threshold proof failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if stress_adapter is not None:
            stress_adapter.close()


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
