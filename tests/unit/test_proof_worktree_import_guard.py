from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.proof_worktree_import_guard import (
    IMPORT_GUARD_ERROR_CODE,
    ensure_worktree_imports,
)


ROOT = Path(__file__).resolve().parents[2]


def test_worktree_import_guard_prefers_entrypoint_worktree_src(
    tmp_path: Path,
) -> None:
    exact_worktree = _worktree_with_app(tmp_path / "exact-worktree", marker="exact")
    sibling_worktree = _worktree_with_app(tmp_path / "sibling-worktree", marker="sibling")
    entrypoint = exact_worktree / "scripts" / "proofs" / "generate.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("# proof generator entrypoint\n", encoding="utf-8")

    code = (
        "from scripts.proof_worktree_import_guard import ensure_worktree_imports\n"
        f"ensure_worktree_imports({str(entrypoint)!r})\n"
        "import app\n"
        "print(app.WORKTREE_MARKER)\n"
        "print(app.__file__)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        env=_pythonpath_env(f"{sibling_worktree / 'src'};{ROOT}"),
        text=True,
    )

    lines = result.stdout.splitlines()
    assert lines[0] == "exact"
    assert Path(lines[1]).resolve().is_relative_to(exact_worktree.resolve())


def test_worktree_import_guard_fails_if_app_was_already_loaded_from_sibling(
    tmp_path: Path,
) -> None:
    exact_worktree = _worktree_with_app(tmp_path / "exact-worktree", marker="exact")
    sibling_worktree = _worktree_with_app(tmp_path / "sibling-worktree", marker="sibling")
    entrypoint = exact_worktree / "scripts" / "proofs" / "generate.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("# proof generator entrypoint\n", encoding="utf-8")

    code = (
        "import app\n"
        "from scripts.proof_worktree_import_guard import ensure_worktree_imports\n"
        f"ensure_worktree_imports({str(entrypoint)!r})\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        env=_pythonpath_env(f"{sibling_worktree / 'src'};{ROOT}"),
        text=True,
    )

    assert result.returncode != 0
    assert IMPORT_GUARD_ERROR_CODE in result.stderr


def test_app_importing_scripts_call_worktree_guard_before_app_imports() -> None:
    offenders: list[str] = []
    for script in (ROOT / "scripts").rglob("*.py"):
        relative_script = script.relative_to(ROOT).as_posix()
        if relative_script == "scripts/proof_worktree_import_guard.py":
            continue
        lines = script.read_text(encoding="utf-8").splitlines()
        first_app_import = _first_index(lines, ("from app", "import app."))
        if first_app_import is None:
            continue
        guard_call = _first_index(lines, ("ensure_worktree_imports(__file__)",))
        if guard_call is None or guard_call > first_app_import:
            offenders.append(relative_script)

    assert offenders == []


def test_worktree_import_guard_rejects_non_repository_entrypoint(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=IMPORT_GUARD_ERROR_CODE):
        ensure_worktree_imports(tmp_path / "scripts" / "generate.py")


def _worktree_with_app(path: Path, *, marker: str) -> Path:
    (path / "scripts").mkdir(parents=True)
    app_package = path / "src" / "app"
    app_package.mkdir(parents=True)
    (app_package / "__init__.py").write_text(
        f"WORKTREE_MARKER = {marker!r}\n",
        encoding="utf-8",
    )
    return path


def _pythonpath_env(pythonpath: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    return env


def _first_index(lines: list[str], prefixes: tuple[str, ...]) -> int | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in prefixes):
            return index
    return None
