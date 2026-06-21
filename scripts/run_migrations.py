from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import cast

from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    build_migration_plan,
    dry_run_migration_plan,
    execute_migration_plan,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run lotus-idea PostgreSQL migrations.")
    parser.add_argument(
        "--direction",
        choices=[direction.value for direction in MigrationDirection],
        default=MigrationDirection.APPLY.value,
    )
    parser.add_argument("--database-url", default=os.getenv("LOTUS_IDEA_DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    direction = MigrationDirection(args.direction)
    plan = build_migration_plan(MIGRATIONS_DIR, direction)

    if args.dry_run:
        records = dry_run_migration_plan(plan)
        for record in records:
            print(
                f"{record.direction.value} {record.version}_{record.name}: "
                f"{record.statement_count} statements"
            )
        print("Migration dry run passed")
        return 0

    if not args.database_url:
        print("LOTUS_IDEA_DATABASE_URL or --database-url is required for migration execution")
        return 2

    import psycopg

    with psycopg.connect(args.database_url) as connection:
        records = execute_migration_plan(cast(MigrationConnection, connection), plan)
    for record in records:
        print(
            f"{record.direction.value} {record.version}_{record.name}: "
            f"{record.statement_count} statements"
        )
    print("Migration execution passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
