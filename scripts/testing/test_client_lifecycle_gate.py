from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_TEST_ROOT = ROOT / "tests" / "integration"
PROHIBITED_MODULES = frozenset({"fastapi.testclient", "starlette.testclient"})


def find_unmanaged_test_client_violations(test_root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(test_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        direct_names: set[str] = set()
        module_aliases: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in PROHIBITED_MODULES:
                for imported in node.names:
                    if imported.name == "TestClient":
                        direct_names.add(imported.asname or imported.name)
                        violations.append(
                            _format(path, node.lineno, "import managed_test_client instead")
                        )
            elif isinstance(node, ast.Import):
                for imported in node.names:
                    if imported.name in PROHIBITED_MODULES:
                        module_aliases.add(imported.asname or imported.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in direct_names:
                violations.append(
                    _format(path, node.lineno, "unmanaged TestClient construction is prohibited")
                )
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "TestClient"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in module_aliases
            ):
                violations.append(
                    _format(path, node.lineno, "unmanaged TestClient construction is prohibited")
                )
    return sorted(violations)


def _format(path: Path, line: int, message: str) -> str:
    relative_path = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    return f"{relative_path}:{line}: {message}"


def main() -> int:
    violations = find_unmanaged_test_client_violations(INTEGRATION_TEST_ROOT)
    if violations:
        print("Integration TestClient lifecycle gate failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Integration TestClient lifecycle gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
