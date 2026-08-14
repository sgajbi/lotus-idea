from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_closure_matrix_gate.py"
    spec = importlib.util.spec_from_file_location("github_issue_closure_matrix_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_github_issue_closure_matrix_gate_freezes_rfc0002_stale_closed_rows(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    stale_closed_issues = {
        650,
        652,
        653,
        654,
        655,
        656,
        657,
        658,
        659,
        661,
        662,
        663,
        664,
        666,
    }
    lines = []
    for line in content.splitlines():
        if any(line.startswith(f"| [#{issue}](") for issue in stale_closed_issues):
            line = line.replace("| `merged_main` |", "| `locally_fixed` |", 1)
        lines.append(line)
    matrix.write_text("\n".join(lines) + "\n", encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    for issue in stale_closed_issues:
        assert f"#{issue}: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_latest_outbox_readiness_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Refactor outbox delivery readiness PostgreSQL summary projection | `merged_main` |",
        "Refactor outbox delivery readiness PostgreSQL summary projection | `locally_fixed` |",
        1,
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#1088: merged-main issue cannot regress to `locally_fixed`" in errors
