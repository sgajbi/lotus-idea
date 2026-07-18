from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANAGED_TEST_ROOTS = (
    ROOT / "tests" / "integration",
    ROOT / "tests" / "e2e",
)
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
                            _format(
                                path,
                                test_root,
                                node.lineno,
                                "import managed_test_client instead",
                            )
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
                    _format(
                        path,
                        test_root,
                        node.lineno,
                        "unmanaged TestClient construction is prohibited",
                    )
                )
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "TestClient"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in module_aliases
            ):
                violations.append(
                    _format(
                        path,
                        test_root,
                        node.lineno,
                        "unmanaged TestClient construction is prohibited",
                    )
                )
    return sorted(violations)


def _format(path: Path, test_root: Path, line: int, message: str) -> str:
    if path.is_relative_to(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
    elif test_root.name in {"integration", "e2e"} and test_root.parent.name == "tests":
        relative_path = path.relative_to(test_root.parent.parent).as_posix()
    else:
        relative_path = path.name
    return f"{relative_path}:{line}: {message}"


def main() -> int:
    violations = [
        violation
        for test_root in MANAGED_TEST_ROOTS
        for violation in find_unmanaged_test_client_violations(test_root)
    ]
    if violations:
        print("Managed TestClient lifecycle gate failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Managed TestClient lifecycle gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
