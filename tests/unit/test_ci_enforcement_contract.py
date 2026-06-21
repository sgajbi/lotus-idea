from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_architecture_boundary_gate_is_blocking_in_local_ci() -> None:
    makefile = _read("Makefile")

    assert "architecture-boundary-gate:" in makefile
    assert "scripts/architecture_boundary_gate.py --mode blocking" in makefile
    assert "check: lint typecheck architecture-boundary-gate" in makefile
    assert "ci: lint typecheck architecture-boundary-gate" in makefile


def test_architecture_boundary_gate_runs_in_github_lanes() -> None:
    for workflow in (
        ".github/workflows/feature-lane.yml",
        ".github/workflows/pr-merge-gate.yml",
        ".github/workflows/main-releasability.yml",
    ):
        content = _read(workflow)
        assert "Architecture Boundary Gate" in content
        assert "make architecture-boundary-gate" in content


def test_generated_quality_reports_do_not_dirty_worktree() -> None:
    gitignore = _read(".gitignore")

    assert "quality/architecture_boundary_report.json" in gitignore
    assert "quality/baseline_report.json" in gitignore
    assert "quality/baseline_report.md" in gitignore
