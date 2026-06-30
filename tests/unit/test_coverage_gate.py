from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _load_coverage_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "coverage_gate.py"
    spec = importlib.util.spec_from_file_location("coverage_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_coverage_gate_reports_missing_artifacts(tmp_path: Path, capsys: Any) -> None:
    module = _load_coverage_gate()

    assert module.main(["--coverage-dir", str(tmp_path)]) == 1

    captured = capsys.readouterr()
    assert "Missing coverage files" in captured.out
    assert ".coverage.unit" in captured.out


def test_coverage_gate_combines_artifacts_from_configured_directory(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_coverage_gate()
    for name in module.DEFAULT_COVERAGE_FILES:
        (tmp_path / name).write_text("coverage", encoding="utf-8")
    fake_coverage = FakeCoverage()
    monkeypatch.setattr(module.coverage, "Coverage", lambda: fake_coverage)

    assert module.main(["--coverage-dir", str(tmp_path)]) == 0

    assert fake_coverage.combined_files == [
        tmp_path / name for name in module.DEFAULT_COVERAGE_FILES
    ]
    assert fake_coverage.saved is True


def test_coverage_gate_fails_under_threshold(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_coverage_gate()
    for name in module.DEFAULT_COVERAGE_FILES:
        (tmp_path / name).write_text("coverage", encoding="utf-8")
    fake_coverage = FakeCoverage(total=98.9)
    monkeypatch.setattr(module.coverage, "Coverage", lambda: fake_coverage)

    assert module.main(["--coverage-dir", str(tmp_path)]) == 1


class FakeCoverage:
    def __init__(self, *, total: float = 99.2) -> None:
        self.total = total
        self.combined_files: list[Path] = []
        self.saved = False

    def combine(self, files: list[Path]) -> None:
        self.combined_files = files

    def save(self) -> None:
        self.saved = True

    def report(self) -> float:
        return self.total
