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


def test_github_issue_closure_matrix_gate_passes_current_matrix() -> None:
    module = _load_gate()

    assert module.validate_issue_closure_matrix() == []


def test_github_issue_closure_matrix_gate_blocks_missing_issue(tmp_path: Path) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    matrix.write_text(
        "# Matrix\n\n"
        "| Issue | Status | Implementation Evidence | Test And Gate Evidence | Same-Pattern Scan | Docs/Wiki/Context | PR Close Intent |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| #301 | `locally_fixed` | `src/app/api/signal_api_support.py` | `tests/unit/test_signal_api_support.py` | same-pattern scan done | `REPOSITORY-ENGINEERING-CONTEXT.md` | Closes #301 |\n",
        encoding="utf-8",
    )

    errors = module.validate_issue_closure_matrix(matrix)

    assert any("Missing actionable issue rows: #302" in error for error in errors)


def test_github_issue_closure_matrix_gate_blocks_weak_evidence(tmp_path: Path) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    rows = []
    for issue in sorted(module.ACTIONABLE_ISSUES):
        implementation = "`src/app/api/example.py`"
        tests = "`tests/unit/test_example.py`"
        scan = "same-pattern scan done"
        docs = "`REPOSITORY-ENGINEERING-CONTEXT.md`"
        close = f"Closes #{issue}"
        if issue == 302:
            implementation = "not recorded"
            tests = "not recorded"
            scan = "not recorded"
            docs = "not recorded"
            close = "close later"
        rows.append(
            f"| #{issue} | `locally_fixed` | {implementation} | {tests} | {scan} | {docs} | {close} |"
        )
    matrix.write_text(
        "# Matrix\n\n"
        "| Issue | Status | Implementation Evidence | Test And Gate Evidence | Same-Pattern Scan | Docs/Wiki/Context | PR Close Intent |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#302: implementation evidence must cite code or contract paths" in errors
    assert (
        "#302: test and gate evidence must cite tests, make targets, or an executed workflow "
        "dispatch" in errors
    )
    assert "#302: same-pattern scan evidence is required" in errors
    assert "#302: docs/wiki/context evidence or decision is required" in errors
    assert "#302: locally fixed intent must contain `Closes #302`" in errors


def test_github_issue_closure_matrix_gate_rejects_partial_status_with_close_intent(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace("Keep #343 open", "Closes #343")
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert (
        "#343: partially fixed intent must contain `Keep #343 open` or `Keeps #343 open`" in errors
    )
