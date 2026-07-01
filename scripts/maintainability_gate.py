from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ast_function_helpers import is_non_implementation_stub
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from ast_function_helpers import is_non_implementation_stub

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ScopeLimit:
    name: str
    relative_path: str
    max_file_lines: int
    max_function_lines: int


SCOPE_LIMITS = (
    ScopeLimit("source", "src", max_file_lines=1200, max_function_lines=130),
    ScopeLimit("tests", "tests", max_file_lines=1200, max_function_lines=180),
    ScopeLimit("scripts", "scripts", max_file_lines=500, max_function_lines=120),
)


def _python_files(scope_root: Path) -> list[Path]:
    if not scope_root.exists():
        return []
    return sorted(path for path in scope_root.rglob("*.py") if "__pycache__" not in path.parts)


def _function_rows(path: Path) -> list[tuple[str, int, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_non_implementation_stub(node):
                continue
            end_line = getattr(node, "end_lineno", node.lineno)
            rows.append((node.name, node.lineno, end_line - node.lineno + 1))
    return rows


def validate_maintainability(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for limit in SCOPE_LIMITS:
        scope_root = root / limit.relative_path
        for path in _python_files(scope_root):
            relative_path = path.relative_to(root).as_posix()
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > limit.max_file_lines:
                violations.append(
                    f"{relative_path} has {lines} lines; {limit.name} files must stay at or below "
                    f"{limit.max_file_lines} lines"
                )
            for function_name, line_number, function_lines in _function_rows(path):
                if function_lines > limit.max_function_lines:
                    violations.append(
                        f"{relative_path}:{line_number} `{function_name}` has {function_lines} "
                        f"lines; {limit.name} functions must stay at or below "
                        f"{limit.max_function_lines} lines"
                    )
    return violations


def main() -> int:
    violations = validate_maintainability()
    if violations:
        print("Maintainability gate failed:")
        print("\n".join(violations))
        return 1
    print("Maintainability gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
