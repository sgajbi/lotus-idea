from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

import pytest

from app.infrastructure.postgres_backup_restore import (
    PostgresBackupRestoreCommandError,
    PostgresLogicalBackupRestore,
)

SOURCE_URL = "postgresql://source-user:source-secret@source-db:5432/source_idea"
TARGET_URL = "postgresql://target-user:target-secret@target-db:5432/target_idea"
CHECKPOINT = datetime(2026, 7, 11, 5, 0, tzinfo=UTC)


class FakeCursor:
    def __init__(self, result: object) -> None:
        self.result = result

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, _query: str) -> None:
        return None

    def fetchone(self) -> tuple[object]:
        return (self.result,)


class FakeConnection:
    def __init__(self, result: object) -> None:
        self.result = result

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.result)


def test_logical_restore_uses_secret_safe_commands_and_ephemeral_credentials() -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []
    times = iter(
        (
            CHECKPOINT - timedelta(seconds=1),
            CHECKPOINT + timedelta(seconds=2),
            CHECKPOINT + timedelta(seconds=5),
        )
    )

    def connect(database_url: str) -> FakeConnection:
        return FakeConnection(CHECKPOINT if database_url == SOURCE_URL else 0)

    def run_command(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        environment = kwargs["env"]
        if os.name != "nt":
            assert stat.S_IMODE(Path(environment["PGPASSFILE"]).stat().st_mode) == 0o600
        calls.append((command, environment))
        if command[0] == "pg_dump":
            dump_path = Path(command[command.index("--file") + 1])
            dump_path.write_bytes(b"source-safe-logical-backup")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = PostgresLogicalBackupRestore(
        run_command=run_command,
        connect=connect,
        now=lambda: next(times),
    ).execute(source_database_url=SOURCE_URL, target_database_url=TARGET_URL)

    assert result.backup_format == "postgres-custom-logical"
    assert result.pitr_proof is False
    assert len(result.backup_artifact_sha256) == 64
    assert result.recovery_point_utc == CHECKPOINT
    assert [call[0][0] for call in calls] == ["pg_dump", "pg_restore"]
    flattened_commands = " ".join(part for command, _ in calls for part in command)
    assert "secret" not in flattened_commands
    assert "postgresql://" not in flattened_commands
    assert all("PGPASSWORD" not in environment for _, environment in calls)
    assert all("LOTUS_IDEA_DR_SOURCE_DATABASE_URL" not in environment for _, environment in calls)
    passfiles = {environment["PGPASSFILE"] for _, environment in calls}
    assert len(passfiles) == 1
    assert not Path(passfiles.pop()).exists()


def test_logical_restore_rejects_same_database_and_nonempty_target() -> None:
    runner = PostgresLogicalBackupRestore(connect=lambda _url: FakeConnection(1))

    with pytest.raises(ValueError, match="must differ"):
        runner.execute(source_database_url=SOURCE_URL, target_database_url=SOURCE_URL)
    with pytest.raises(ValueError, match="must not contain user tables"):
        runner.execute(source_database_url=SOURCE_URL, target_database_url=TARGET_URL)


def test_logical_restore_rejects_naive_operator_clock() -> None:
    def connect(database_url: str) -> FakeConnection:
        return FakeConnection(CHECKPOINT if database_url == SOURCE_URL else 0)

    runner = PostgresLogicalBackupRestore(
        connect=connect,
        now=lambda: datetime(2026, 7, 11, 5, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        runner.execute(source_database_url=SOURCE_URL, target_database_url=TARGET_URL)


@pytest.mark.parametrize(
    "failed_command, expected_phase, bytes_stderr",
    [("pg_dump", "backup", False), ("pg_restore", "restore", True)],
)
def test_logical_restore_reports_source_safe_command_failure(
    failed_command: str,
    expected_phase: str,
    bytes_stderr: bool,
) -> None:
    def connect(database_url: str) -> FakeConnection:
        return FakeConnection(CHECKPOINT if database_url == SOURCE_URL else 0)

    def run_command(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[0] == "pg_dump":
            dump_path = Path(command[command.index("--file") + 1])
            dump_path.write_bytes(b"source-safe-logical-backup")
        if command[0] == failed_command:
            settings = (
                ("source-db", "source_idea", "source-user", "source-secret")
                if failed_command == "pg_dump"
                else ("target-db", "target_idea", "target-user", "target-secret")
            )
            diagnostic = (
                f"connection to {settings[0]}/{settings[1]} as {settings[2]} "
                f"failed using {settings[3]}"
            )
            raise subprocess.CalledProcessError(
                1,
                command,
                stderr=diagnostic.encode() if bytes_stderr else diagnostic,
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    runner = PostgresLogicalBackupRestore(
        run_command=run_command,
        connect=connect,
        now=lambda: CHECKPOINT,
    )

    with pytest.raises(PostgresBackupRestoreCommandError) as captured:
        runner.execute(source_database_url=SOURCE_URL, target_database_url=TARGET_URL)

    message = str(captured.value)
    assert f"logical {expected_phase} command failed with exit code 1" in message
    assert "<host>/<database> as <user>" in message
    for sensitive_value in (
        "source-db",
        "source_idea",
        "source-user",
        "source-secret",
        "target-db",
        "target_idea",
        "target-user",
        "target-secret",
    ):
        assert sensitive_value not in message
