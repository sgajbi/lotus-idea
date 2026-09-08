from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from typing import Sequence


POSTGRES_FIXTURE_NAME = "postgres_database_url"


def discover_postgres_test_paths(integration_root: Path) -> tuple[Path, ...]:
    """Return tests that directly request the governed PostgreSQL fixture."""
    selected: list[Path] = []
    for path in sorted(integration_root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(_requests_postgres_fixture(node) for node in ast.walk(tree)):
            selected.append(path)
    return tuple(selected)


def _requests_postgres_fixture(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if not node.name.startswith("test_"):
        return False
    arguments = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    return any(argument.arg == POSTGRES_FIXTURE_NAME for argument in arguments)


def run_postgres_integration_gate(
    integration_root: Path,
    pytest_arguments: Sequence[str],
) -> int:
    selected = discover_postgres_test_paths(integration_root)
    if not selected:
        raise RuntimeError(
            f"no tests request the {POSTGRES_FIXTURE_NAME!r} fixture under {integration_root}"
        )
    relative_paths = tuple(path.as_posix() for path in selected)
    print(f"PostgreSQL integration gate selected {len(relative_paths)} test files:")
    print("\n".join(f"- {path}" for path in relative_paths))
    command = (sys.executable, "-m", "pytest", *relative_paths, *pytest_arguments)
    return subprocess.run(command, check=False).returncode


def main(arguments: Sequence[str] | None = None) -> int:
    return run_postgres_integration_gate(
        Path("tests/integration"),
        tuple(arguments if arguments is not None else sys.argv[1:]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
