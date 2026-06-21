from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_migration_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "migration_contract_gate.py"
    spec = importlib.util.spec_from_file_location("migration_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_contract_gate_passes_current_repository_contract() -> None:
    module = _load_migration_contract_gate()

    assert module.validate_migration_contracts() == []


def test_migration_contract_gate_blocks_missing_rollback(tmp_path: Path) -> None:
    module = _load_migration_contract_gate()
    forward = tmp_path / "001_idea_repository_foundation.sql"
    rollback = tmp_path / "001_idea_repository_foundation.rollback.sql"
    forward.write_text(
        (ROOT / "migrations" / "001_idea_repository_foundation.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    migration = module.MigrationContract("001", forward, rollback)

    assert module.validate_migration_contracts((migration,)) == [
        f"Migration 001 missing rollback {rollback.as_posix()}"
    ]


def test_migration_contract_gate_blocks_missing_required_table(tmp_path: Path) -> None:
    module = _load_migration_contract_gate()
    forward = tmp_path / "001_idea_repository_foundation.sql"
    rollback = tmp_path / "001_idea_repository_foundation.rollback.sql"
    forward.write_text(
        (ROOT / "migrations" / "001_idea_repository_foundation.sql")
        .read_text(encoding="utf-8")
        .replace(
            "CREATE TABLE IF NOT EXISTS idea_audit_event",
            "CREATE TABLE IF NOT EXISTS idea_event",
        ),
        encoding="utf-8",
    )
    rollback.write_text(
        (ROOT / "migrations" / "001_idea_repository_foundation.rollback.sql").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    migration = module.MigrationContract("001", forward, rollback)
    errors = module.validate_migration_contracts((migration,))

    assert "Migration 001 missing table `idea_audit_event`" in errors


def test_migration_contract_gate_blocks_missing_rollback_table(tmp_path: Path) -> None:
    module = _load_migration_contract_gate()
    forward = tmp_path / "001_idea_repository_foundation.sql"
    rollback = tmp_path / "001_idea_repository_foundation.rollback.sql"
    forward.write_text(
        (ROOT / "migrations" / "001_idea_repository_foundation.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    rollback.write_text(
        (ROOT / "migrations" / "001_idea_repository_foundation.rollback.sql")
        .read_text(encoding="utf-8")
        .replace("DROP TABLE IF EXISTS idea_candidate_record;", ""),
        encoding="utf-8",
    )

    migration = module.MigrationContract("001", forward, rollback)
    errors = module.validate_migration_contracts((migration,))

    assert "Migration 001 rollback missing table `idea_candidate_record`" in errors
