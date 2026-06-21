from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_architecture_boundary_gate_is_blocking_in_local_ci() -> None:
    makefile = _read("Makefile")

    assert "architecture-boundary-gate:" in makefile
    assert "scripts/architecture_boundary_gate.py --mode blocking" in makefile
    assert "check: lint typecheck architecture-boundary-gate" in makefile
    assert "ci: lint typecheck architecture-boundary-gate" in makefile
    assert "ci-contract-gate:" in makefile
    assert "$(MAKE) ci-contract-gate" in makefile
    assert "data-mesh-contract-gate:" in makefile
    assert "$(MAKE) data-mesh-contract-gate" in makefile


def test_architecture_boundary_gate_runs_in_github_lanes() -> None:
    for workflow in (
        ".github/workflows/feature-lane.yml",
        ".github/workflows/pr-merge-gate.yml",
        ".github/workflows/main-releasability.yml",
    ):
        content = _read(workflow)
        assert "Architecture Boundary Gate" in content
        assert "make architecture-boundary-gate" in content


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_passes_current_repository_contract() -> None:
    module = _load_ci_contract_gate()

    assert module.validate_ci_contract() == []


def test_ci_contract_gate_blocks_missing_merge_grade_checks() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("security-audit", "security-report")

    errors = module.validate_makefile(makefile)

    assert "Makefile missing required target `security-audit`" in errors
    assert "Makefile ci target missing `security-audit`" in errors


def test_ci_contract_gate_blocks_write_permissions_in_read_only_lanes(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace("contents: read", "contents: write"),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml must not contain `contents: write`" in errors


def test_generated_quality_reports_do_not_dirty_worktree() -> None:
    gitignore = _read(".gitignore")

    assert "quality/architecture_boundary_report.json" in gitignore
    assert "quality/baseline_report.json" in gitignore
    assert "quality/baseline_report.md" in gitignore


def _load_architecture_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "architecture_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("architecture_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_blocking_architecture_boundary_gate_does_not_write_report(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    report_path = tmp_path / "architecture_boundary_report.json"

    monkeypatch.setattr(module, "REPORT_PATH", report_path)
    monkeypatch.setattr(module, "validate_architecture_boundaries", lambda: [])
    monkeypatch.setattr(sys, "argv", ["architecture_boundary_gate.py", "--mode", "blocking"])

    assert module.main() == 0

    assert not report_path.exists()
    assert "Architecture boundary gate passed" in capsys.readouterr().out


def test_report_only_architecture_boundary_gate_writes_report(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    report_path = tmp_path / "architecture_boundary_report.json"

    monkeypatch.setattr(module, "REPORT_PATH", report_path)
    monkeypatch.setattr(module, "validate_architecture_boundaries", lambda: [])
    monkeypatch.setattr(sys, "argv", ["architecture_boundary_gate.py", "--mode", "report-only"])

    assert module.main() == 0

    assert report_path.exists()
    assert "Architecture boundary report passed" in capsys.readouterr().out
