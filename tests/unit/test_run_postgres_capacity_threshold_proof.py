from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.domain.capacity_posture import evaluate_postgres_capacity_posture


ROOT = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "run_postgres_capacity_threshold_proof.py"
    spec = importlib.util.spec_from_file_location("run_postgres_capacity_threshold_proof", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arguments(module: ModuleType, output: Path) -> list[str]:
    return [
        "--environment-profile",
        "test",
        "--expected-database-name",
        "idea_capacity_proof",
        "--maximum-target-connections",
        "20",
        "--confirmation",
        module.CONFIRMATION,
        "--commit-sha",
        "abc123",
        "--branch",
        "feature/capacity",
        "--run-id",
        "local-1",
        "--output",
        str(output),
    ]


def test_cli_writes_source_safe_evidence_and_closes_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    output = tmp_path / "proof.json"

    class FakeAdapter:
        instance: "FakeAdapter"

        def __init__(self, **kwargs: object) -> None:
            self.postures = iter([0.2, 0.9, 0.2])
            self.closed = False
            FakeAdapter.instance = self

        def read_posture(self):  # type: ignore[no-untyped-def]
            return evaluate_postgres_capacity_posture(next(self.postures))

        def acquire_load_connection(self) -> None:
            pass

        def release_load_connections(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    monkeypatch.setenv(module.DATABASE_URL_ENV, "postgresql://secret-not-persisted")
    monkeypatch.setattr(module, "PostgresCapacityStressAdapter", FakeAdapter)

    assert module.main(_arguments(module, output)) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["threshold"]["posture"] == "shed"
    assert artifact["productionCapacityCertified"] is False
    assert "secret-not-persisted" not in output.read_text(encoding="utf-8")
    assert FakeAdapter.instance.closed is True


def test_cli_rejects_wrong_confirmation_before_connecting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    arguments = _arguments(module, tmp_path / "proof.json")
    arguments[arguments.index(module.CONFIRMATION)] = "yes"
    monkeypatch.setenv(module.DATABASE_URL_ENV, "postgresql://secret")

    class UnexpectedAdapter:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("adapter must not be constructed")

    monkeypatch.setattr(module, "PostgresCapacityStressAdapter", UnexpectedAdapter)

    assert module.main(arguments) == 2


def test_cli_requires_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script()
    monkeypatch.delenv(module.DATABASE_URL_ENV, raising=False)

    assert module.main(_arguments(module, tmp_path / "proof.json")) == 2
