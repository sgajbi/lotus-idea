from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "app"

ALLOWED_LOGGING_MODULES = {
    Path("src/app/observability/logging.py"),
}
LOW_LEVEL_OBSERVABILITY_HELPERS = {"log_event"}
PROHIBITED_LOGGING_ATTRIBUTES = {
    "basicConfig",
    "critical",
    "debug",
    "error",
    "exception",
    "getLogger",
    "info",
    "log",
    "warning",
}


def _python_files(source_root: Path) -> list[Path]:
    if not source_root.exists():
        return []
    return sorted(path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_allowed_logging_module(path: Path, root: Path) -> bool:
    return Path(_relative(path, root)) in ALLOWED_LOGGING_MODULES


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _validate_file(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    allowed_logging_module = _is_allowed_logging_module(path, root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "logging" and not allowed_logging_module:
                    errors.append(
                        f"{relative_path}:{node.lineno}: direct logging imports are only "
                        "allowed in src/app/observability/logging.py"
                    )

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = {alias.name for alias in node.names}
            if module == "logging" and not allowed_logging_module:
                errors.append(
                    f"{relative_path}:{node.lineno}: direct logging imports are only "
                    "allowed in src/app/observability/logging.py"
                )
            if (
                module in {"app.observability", "app.observability.logging"}
                and LOW_LEVEL_OBSERVABILITY_HELPERS.intersection(imported_names)
                and not allowed_logging_module
            ):
                errors.append(
                    f"{relative_path}:{node.lineno}: import bounded operation-event helpers "
                    "instead of low-level log_event"
                )

        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name == "print":
                errors.append(
                    f"{relative_path}:{node.lineno}: print() is prohibited in application "
                    "source; use bounded structured logging"
                )
            if call_name == "log_event" and not allowed_logging_module:
                errors.append(
                    f"{relative_path}:{node.lineno}: call emit_operation_event or "
                    "emit_foundation_operation_event instead of log_event"
                )
            if (
                call_name
                and call_name.startswith("logging.")
                and call_name.removeprefix("logging.") in PROHIBITED_LOGGING_ATTRIBUTES
                and not allowed_logging_module
            ):
                errors.append(
                    f"{relative_path}:{node.lineno}: direct logging calls are only allowed in "
                    "src/app/observability/logging.py"
                )

    return errors


def validate_source_observability_contract(root: Path = ROOT) -> list[str]:
    source_root = root / "src" / "app"
    errors: list[str] = []
    for path in _python_files(source_root):
        errors.extend(_validate_file(path, root))
    return sorted(errors)


def main() -> int:
    errors = validate_source_observability_contract()
    if errors:
        print("Source observability contract gate failed:")
        print("\n".join(errors))
        return 1
    print("Source observability contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
