from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.postgres_integration_gate import (
    discover_postgres_test_paths,
    run_postgres_integration_gate,
)


def test_discovers_every_test_file_that_requests_postgres_fixture(tmp_path: Path) -> None:
    selected = tmp_path / "test_selected.py"
    selected.write_text(
        "def test_runtime(postgres_database_url: str) -> None:\n    assert postgres_database_url\n",
        encoding="utf-8",
    )
    nested = tmp_path / "persistence" / "test_new_runtime.py"
    nested.parent.mkdir()
    nested.write_text(
        "async def test_nested(*, postgres_database_url: str) -> None:\n"
        "    assert postgres_database_url\n",
        encoding="utf-8",
    )
    (tmp_path / "test_not_selected.py").write_text(
        "POSTGRES_FIXTURE = 'postgres_database_url'\n"
        "def helper(postgres_database_url: str) -> None:\n"
        "    assert postgres_database_url\n"
        "def test_unit() -> None:\n"
        "    assert POSTGRES_FIXTURE\n",
        encoding="utf-8",
    )

    assert discover_postgres_test_paths(tmp_path) == (nested, selected)


def test_rejects_invalid_python_in_candidate_test_file(tmp_path: Path) -> None:
    invalid = tmp_path / "test_invalid.py"
    invalid.write_text("def broken(:\n", encoding="utf-8")

    with pytest.raises(SyntaxError):
        discover_postgres_test_paths(tmp_path)


def test_gate_executes_the_exact_derived_file_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "test_new_postgres_proof.py"
    selected.write_text(
        "def test_proof(postgres_database_url: str) -> None:\n    assert postgres_database_url\n",
        encoding="utf-8",
    )
    captured: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        captured.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)

    assert run_postgres_integration_gate(tmp_path, ("--junitxml=proof.xml",)) == 0
    assert captured == [
        (
            sys.executable,
            "-m",
            "pytest",
            selected.as_posix(),
            "--junitxml=proof.xml",
        )
    ]


def test_gate_refuses_to_pass_without_postgres_tests(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no tests request"):
        run_postgres_integration_gate(tmp_path, ())


def test_current_gate_includes_every_direct_postgres_fixture_consumer() -> None:
    selected = discover_postgres_test_paths(Path("tests/integration"))

    assert Path("tests/integration/test_postgres_disaster_recovery.py") in selected
    assert Path("tests/integration/test_advise_lost_response_postgres_chain.py") in selected
    assert Path("tests/integration/test_postgres_downstream_submission_runtime.py") in selected
    assert (
        Path("tests/integration/persistence/test_idempotency_storage_identity_migration_runtime.py")
        in selected
    )
