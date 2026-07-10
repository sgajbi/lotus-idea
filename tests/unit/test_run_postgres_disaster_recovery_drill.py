from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from app.domain.disaster_recovery import RestoredDatabaseSnapshot, RestoreValidationStatus
from app.infrastructure.postgres_backup_restore import LogicalRestoreResult

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)


class StubBackupRestore:
    def execute(
        self, *, source_database_url: str, target_database_url: str
    ) -> LogicalRestoreResult:
        assert source_database_url == "postgresql://source"
        assert target_database_url == "postgresql://target"
        return LogicalRestoreResult(
            backup_created_at_utc=NOW - timedelta(minutes=20),
            recovery_point_utc=NOW - timedelta(minutes=19),
            restore_started_at_utc=NOW - timedelta(minutes=10),
            restore_completed_at_utc=NOW - timedelta(minutes=1),
            backup_artifact_sha256="a" * 64,
        )


class StubInspector:
    def __init__(self, _database_url: str, snapshot: RestoredDatabaseSnapshot) -> None:
        self.snapshot = snapshot

    def inspect(self, *, expected_tables: frozenset[str]) -> RestoredDatabaseSnapshot:
        assert expected_tables == set(self.snapshot.table_row_counts)
        return self.snapshot


def test_restore_drill_composes_backup_inspection_and_atomic_evidence(tmp_path: Path) -> None:
    module = load_script()
    contract = json.loads(module.CONTRACT_PATH.read_text(encoding="utf-8"))
    tables = frozenset(contract["restore_verification"]["owned_tables"])
    snapshot = valid_snapshot(tables)
    output_path = tmp_path / "restore-evidence.json"

    evidence = module.run_disaster_recovery_drill(
        backup_identifier="backup-ci-001",
        backup_source="ci-disposable-postgres",
        operator_id="github-actions",
        correlation_id="dr-run-001",
        output_path=output_path,
        source_database_url="postgresql://source",
        target_database_url="postgresql://target",
        backup_restore=StubBackupRestore(),
        inspector_factory=lambda url: StubInspector(url, snapshot),
        now=lambda: NOW,
    )

    assert evidence.status is RestoreValidationStatus.PASSED
    assert evidence.pitr_proof is False
    assert evidence.restore_completed_at_utc == (NOW - timedelta(minutes=1)).isoformat()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "passed"
    assert persisted["backup_artifact_sha256"] == "a" * 64
    assert not output_path.with_suffix(".json.tmp").exists()


def test_restore_drill_fails_closed_when_database_environment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script()
    monkeypatch.delenv(module.SOURCE_DATABASE_URL_ENV, raising=False)
    monkeypatch.delenv(module.TARGET_DATABASE_URL_ENV, raising=False)

    with pytest.raises(ValueError, match="are required"):
        module.run_disaster_recovery_drill(
            backup_identifier="backup-ci-001",
            backup_source="ci",
            operator_id="operator",
            correlation_id="dr-run-001",
        )


def test_restore_drill_preserves_failed_evidence_for_investigation(tmp_path: Path) -> None:
    module = load_script()
    contract = json.loads(module.CONTRACT_PATH.read_text(encoding="utf-8"))
    tables = frozenset(contract["restore_verification"]["owned_tables"])
    snapshot = replace(
        valid_snapshot(tables),
        semantic_violation_counts={"outbox_publication_state": 1},
    )
    output_path = tmp_path / "failed-evidence.json"

    evidence = module.run_disaster_recovery_drill(
        backup_identifier="backup-ci-002",
        backup_source="ci-disposable-postgres",
        operator_id="github-actions",
        correlation_id="dr-run-002",
        output_path=output_path,
        source_database_url="postgresql://source",
        target_database_url="postgresql://target",
        backup_restore=StubBackupRestore(),
        inspector_factory=lambda url: StubInspector(url, snapshot),
        now=lambda: NOW,
    )

    assert evidence.status is RestoreValidationStatus.FAILED
    assert "workflow_state_integrity" in evidence.failed_checks
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == "failed"


def test_provider_restored_database_uses_same_validation_use_case(tmp_path: Path) -> None:
    module = load_script()
    contract = json.loads(module.CONTRACT_PATH.read_text(encoding="utf-8"))
    tables = frozenset(contract["restore_verification"]["owned_tables"])
    output_path = tmp_path / "provider-restore-evidence.json"

    evidence = module.validate_restored_database(
        backup_identifier="provider-backup-001",
        backup_source="managed-postgres-pitr",
        operator_id="database-operator",
        correlation_id="incident-001",
        backup_format="physical-base-plus-wal",
        backup_artifact_sha256="d" * 64,
        pitr_proof=True,
        backup_created_at_utc=NOW - timedelta(hours=12),
        incident_cutoff_utc=NOW - timedelta(minutes=5),
        recovery_point_utc=NOW - timedelta(minutes=6),
        restore_started_at_utc=NOW - timedelta(minutes=4),
        restore_completed_at_utc=NOW - timedelta(minutes=1),
        output_path=output_path,
        target_database_url="postgresql://target",
        inspector_factory=lambda url: StubInspector(url, valid_snapshot(tables)),
        now=lambda: NOW,
    )

    assert evidence.status is RestoreValidationStatus.PASSED
    assert evidence.pitr_proof is True
    assert evidence.backup_format == "physical-base-plus-wal"


def test_restore_drill_direct_entrypoint_loads_shared_evidence_writer() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_postgres_disaster_recovery_drill.py"),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--backup-identifier" in completed.stdout


def valid_snapshot(tables: frozenset[str]) -> RestoredDatabaseSnapshot:
    return RestoredDatabaseSnapshot(
        database_identity_sha256="b" * 64,
        postgres_version="PostgreSQL 16",
        table_row_counts={table: 1 for table in tables},
        table_content_sha256={table: "c" * 64 for table in tables},
        missing_primary_key_tables=(),
        unvalidated_constraints=("ck_idea_candidate_record_state_policy_v1",),
        invalid_indexes=(),
        referential_violation_counts={"all_links": 0},
        semantic_violation_counts={"all_states": 0},
    )


def load_script() -> ModuleType:
    path = ROOT / "scripts/run_postgres_disaster_recovery_drill.py"
    spec = importlib.util.spec_from_file_location("run_postgres_disaster_recovery_drill", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
