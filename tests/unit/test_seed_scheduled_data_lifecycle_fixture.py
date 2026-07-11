from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_scheduled_lifecycle_fixture_requires_disposable_confirmation() -> None:
    module = load_script()

    with pytest.raises(ValueError, match="explicit disposable-database confirmation"):
        module.seed_scheduled_data_lifecycle_fixture(
            "postgresql://fixture",
            confirm_disposable_database=False,
        )


def test_scheduled_lifecycle_fixture_is_synthetic_and_non_destructive() -> None:
    source = (ROOT / "scripts/seed_scheduled_data_lifecycle_fixture.py").read_text(encoding="utf-8")

    assert "PB_SG_GLOBAL_BAL_001" not in source
    assert "idea_scheduled_lifecycle_fixture" in source
    assert "synthetic-privacy-reviewer" in source
    assert "synthetic-privacy-approver" in source
    assert "DELETE FROM" not in source.upper()
    assert "TRUNCATE" not in source.upper()


def test_scheduled_lifecycle_fixture_entrypoint_loads() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/seed_scheduled_data_lifecycle_fixture.py"),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--confirm-disposable-database" in completed.stdout


def load_script() -> ModuleType:
    path = ROOT / "scripts/seed_scheduled_data_lifecycle_fixture.py"
    spec = importlib.util.spec_from_file_location("seed_scheduled_data_lifecycle_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
