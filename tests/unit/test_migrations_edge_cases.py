from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.migrations import (
    MigrationDirection,
    build_migration_plan,
    discover_migrations,
    dry_run_migration_plan,
)


def test_discover_migrations_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing migrations directory"):
        discover_migrations(tmp_path / "missing")


def test_discover_migrations_rejects_missing_rollback(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_foundation.sql").write_text(
        "CREATE TABLE idea(id text);", encoding="utf-8"
    )

    with pytest.raises(FileNotFoundError, match="Missing rollback migration"):
        discover_migrations(migrations_dir)


def test_rollback_plan_uses_rollback_files_in_reverse_order(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    for version in ("001", "002"):
        (migrations_dir / f"{version}_step.sql").write_text(
            f"CREATE TABLE idea_{version}(id text);",
            encoding="utf-8",
        )
        (migrations_dir / f"{version}_step.rollback.sql").write_text(
            f"DROP TABLE idea_{version};",
            encoding="utf-8",
        )

    plan = build_migration_plan(migrations_dir, MigrationDirection.ROLLBACK)
    records = dry_run_migration_plan(plan)

    assert [record.version for record in records] == ["002", "001"]
    assert {record.statement_count for record in records} == {1}


def test_discover_migrations_rejects_invalid_migration_identity(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_.sql").write_text("CREATE TABLE idea(id text);", encoding="utf-8")
    (migrations_dir / "001_.rollback.sql").write_text("DROP TABLE idea;", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid migration filename"):
        discover_migrations(migrations_dir)
