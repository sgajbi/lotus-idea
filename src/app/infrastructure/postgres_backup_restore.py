from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping

import psycopg
from psycopg.conninfo import conninfo_to_dict

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
ConnectionFactory = Callable[[str], Any]


@dataclass(frozen=True)
class PostgresConnectionSettings:
    host: str
    port: str
    database: str
    user: str
    password: str
    sslmode: str | None

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (self.host, self.port, self.database, self.user)


@dataclass(frozen=True)
class LogicalRestoreResult:
    backup_created_at_utc: datetime
    recovery_point_utc: datetime
    restore_started_at_utc: datetime
    restore_completed_at_utc: datetime
    backup_artifact_sha256: str
    backup_format: str = "postgres-custom-logical"
    pitr_proof: bool = False


class PostgresLogicalBackupRestore:
    def __init__(
        self,
        *,
        pg_dump_executable: str = "pg_dump",
        pg_restore_executable: str = "pg_restore",
        run_command: CommandRunner = subprocess.run,
        connect: ConnectionFactory = psycopg.connect,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._pg_dump_executable = pg_dump_executable
        self._pg_restore_executable = pg_restore_executable
        self._run_command = run_command
        self._connect = connect
        self._now = now or (lambda: datetime.now(UTC))

    def execute(
        self, *, source_database_url: str, target_database_url: str
    ) -> LogicalRestoreResult:
        source = parse_postgres_connection_settings(source_database_url)
        target = parse_postgres_connection_settings(target_database_url)
        if source.identity == target.identity:
            raise ValueError("source and target PostgreSQL databases must differ")
        _assert_clean_restore_target(self._connect, target_database_url)
        recovery_point = _source_checkpoint(self._connect, source_database_url)
        backup_created_at = self._utc_now()

        with TemporaryDirectory(prefix="lotus-idea-postgres-restore-") as temp_dir:
            temp_path = Path(temp_dir)
            os.chmod(temp_path, 0o700)
            dump_path = temp_path / "lotus-idea.dump"
            passfile = temp_path / "pgpass"
            _write_pgpass(passfile, source, target)
            self._run(
                [
                    self._pg_dump_executable,
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    str(dump_path),
                ],
                environment=_postgres_environment(source, passfile),
            )
            artifact_sha256 = _file_sha256(dump_path)
            restore_started_at = self._utc_now()
            self._run(
                [
                    self._pg_restore_executable,
                    "--exit-on-error",
                    "--no-owner",
                    "--no-privileges",
                    str(dump_path),
                ],
                environment=_postgres_environment(target, passfile),
            )
            restore_completed_at = self._utc_now()

        return LogicalRestoreResult(
            backup_created_at_utc=backup_created_at,
            recovery_point_utc=recovery_point,
            restore_started_at_utc=restore_started_at,
            restore_completed_at_utc=restore_completed_at,
            backup_artifact_sha256=artifact_sha256,
        )

    def _run(self, command: list[str], *, environment: Mapping[str, str]) -> None:
        self._run_command(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=dict(environment),
        )

    def _utc_now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("backup/restore clock must return timezone-aware UTC")
        return value


def parse_postgres_connection_settings(database_url: str) -> PostgresConnectionSettings:
    if not database_url.strip():
        raise ValueError("PostgreSQL database URL is required")
    values = conninfo_to_dict(database_url)
    database = _conninfo_text(values.get("dbname")).strip()
    user = _conninfo_text(values.get("user")).strip()
    if not database or not user:
        raise ValueError("PostgreSQL database URL must identify database and user")
    return PostgresConnectionSettings(
        host=_conninfo_text(values.get("host")) or "localhost",
        port=_conninfo_text(values.get("port")) or "5432",
        database=database,
        user=user,
        password=_conninfo_text(values.get("password")),
        sslmode=_conninfo_text(values.get("sslmode")) or None,
    )


def _conninfo_text(value: str | int | None) -> str:
    return "" if value is None else str(value)


def _assert_clean_restore_target(connect: ConnectionFactory, database_url: str) -> None:
    with connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) FROM pg_catalog.pg_tables
                   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"""
            )
            table_count = int(cursor.fetchone()[0])
    if table_count:
        raise ValueError("restore target must not contain user tables")


def _source_checkpoint(connect: ConnectionFactory, database_url: str) -> datetime:
    with connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT clock_timestamp()")
            checkpoint = cursor.fetchone()[0]
    if not isinstance(checkpoint, datetime):
        raise TypeError("PostgreSQL checkpoint query did not return a timestamp")
    if checkpoint.tzinfo is None or checkpoint.utcoffset() != UTC.utcoffset(checkpoint):
        raise ValueError("PostgreSQL checkpoint must be timezone-aware UTC")
    return checkpoint


def _write_pgpass(
    path: Path,
    source: PostgresConnectionSettings,
    target: PostgresConnectionSettings,
) -> None:
    entries = {_pgpass_entry(source), _pgpass_entry(target)}
    path.write_text("\n".join(sorted(entries)) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _pgpass_entry(settings: PostgresConnectionSettings) -> str:
    values = (
        settings.host,
        settings.port,
        settings.database,
        settings.user,
        settings.password,
    )
    return ":".join(_escape_pgpass(value) for value in values)


def _escape_pgpass(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:")


def _postgres_environment(settings: PostgresConnectionSettings, passfile: Path) -> dict[str, str]:
    environment = {
        key: value
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP")
        if (value := os.environ.get(key))
    }
    environment.update(
        {
            "PGHOST": settings.host,
            "PGPORT": settings.port,
            "PGDATABASE": settings.database,
            "PGUSER": settings.user,
            "PGPASSFILE": str(passfile),
        }
    )
    if settings.sslmode:
        environment["PGSSLMODE"] = settings.sslmode
    return environment


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
