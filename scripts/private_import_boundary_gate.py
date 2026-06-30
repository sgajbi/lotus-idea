from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("src", "tests", "scripts")
PROTECTED_IMPORT_PREFIXES = ("app.domain.",)


def _python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative_root in SCAN_ROOTS:
        scan_root = root / relative_root
        if not scan_root.exists():
            continue
        files.extend(
            path
            for path in scan_root.rglob("*.py")
            if "__pycache__" not in path.parts and path.is_file()
        )
    return sorted(files)


def _module_name(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root).with_suffix("")
    if relative.parts[0] == "src":
        return ".".join(relative.parts[1:])
    if relative.parts[0] in {"tests", "scripts"}:
        return ".".join(relative.parts)
    return None


def _is_protected_module(module_name: str) -> bool:
    return module_name == "app.domain" or module_name.startswith(PROTECTED_IMPORT_PREFIXES)


def validate_private_import_boundaries(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for path in _python_files(root):
        source_module = _module_name(path, root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if not _is_protected_module(node.module):
                continue
            if source_module == node.module:
                continue
            for alias in node.names:
                imported_name = alias.name
                if imported_name.startswith("_") and not imported_name.startswith("__"):
                    violations.append(
                        f"{path.relative_to(root).as_posix()}:{node.lineno}: "
                        f"private import `{imported_name}` from `{node.module}` must use a "
                        "public domain API"
                    )
    return violations


def main() -> int:
    violations = validate_private_import_boundaries()
    if violations:
        print("Private import boundary gate failed:")
        print("\n".join(violations))
        return 1
    print("Private import boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
