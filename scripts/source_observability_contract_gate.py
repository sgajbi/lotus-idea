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
SOURCE_AUTHORITY_HASH_OWNERS = {
    Path("src/app/infrastructure/lotus_manage_sources.py"): {
        "json",
        "hashlib",
    },
}
FORBIDDEN_SOURCE_AUTHORITY_TEXT = {
    Path("src/app/infrastructure/lotus_core_sources.py"): {
        "_source_reported_maturity_dates": (
            "Core bond-maturity evidence must consume explicit Core-owned maturity summary "
            "facts, not local raw-position maturity scans"
        ),
        'payload.get("positions")': (
            "Core bond-maturity evidence must consume explicit Core-owned maturity summary "
            "facts, not local raw-position maturity scans"
        ),
        "for position in positions": (
            "Core bond-maturity evidence must consume explicit Core-owned maturity summary "
            "facts, not local raw-position maturity scans"
        ),
    },
}
FRESHNESS_INFERENCE_TEST_TERMS = (
    "supportability",
    "readiness",
    "data_quality",
    "health_state",
    "healthstate",
    "coverage",
)


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
    relative = Path(relative_path)
    allowed_logging_module = _is_allowed_logging_module(path, root)
    prohibited_source_hash_modules = SOURCE_AUTHORITY_HASH_OWNERS.get(relative, set())
    source_text = path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(path))
    errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "logging" and not allowed_logging_module:
                    errors.append(
                        f"{relative_path}:{node.lineno}: direct logging imports are only "
                        "allowed in src/app/observability/logging.py"
                    )
                if alias.name in prohibited_source_hash_modules:
                    errors.append(
                        f"{relative_path}:{node.lineno}: {alias.name} import is prohibited "
                        "because upstream source-ref hashes must be source-authored"
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
            if module in prohibited_source_hash_modules:
                errors.append(
                    f"{relative_path}:{node.lineno}: {module} import is prohibited because "
                    "upstream source-ref hashes must be source-authored"
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
            if call_name in {"hashlib.sha256", "json.dumps"} and prohibited_source_hash_modules:
                errors.append(
                    f"{relative_path}:{node.lineno}: {call_name} fallback is prohibited "
                    "because upstream source-ref hashes must be source-authored"
                )

        if isinstance(node, ast.If) and _is_source_adapter(relative):
            test_source = ast.get_source_segment(source_text, node.test) or ""
            normalized_test = test_source.replace(" ", "").lower()
            if _contains_current_freshness_return(node.body) and any(
                term in normalized_test for term in FRESHNESS_INFERENCE_TEST_TERMS
            ):
                errors.append(
                    f"{relative_path}:{node.lineno}: source adapters must not infer current "
                    "freshness from readiness, supportability, coverage, health-state, or "
                    "data-quality posture"
                )

    for forbidden_text, reason in FORBIDDEN_SOURCE_AUTHORITY_TEXT.get(relative, {}).items():
        line_number = _line_number(source_text, forbidden_text)
        if line_number is not None:
            errors.append(f"{relative_path}:{line_number}: {reason}")

    return errors


def validate_source_observability_contract(root: Path = ROOT) -> list[str]:
    source_root = root / "src" / "app"
    errors: list[str] = []
    for path in _python_files(source_root):
        errors.extend(_validate_file(path, root))
    return sorted(errors)


def _line_number(source_text: str, needle: str) -> int | None:
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        if needle in line:
            return line_number
    return None


def _is_source_adapter(relative: Path) -> bool:
    return (
        len(relative.parts) == 4
        and relative.parts[:3] == ("src", "app", "infrastructure")
        and relative.name.startswith("lotus_")
        and relative.name.endswith("_sources.py")
    )


def _contains_current_freshness_return(nodes: list[ast.stmt]) -> bool:
    for node in nodes:
        if isinstance(node, ast.Return) and _is_current_freshness(node.value):
            return True
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt) and _contains_current_freshness_return([child]):
                return True
    return False


def _is_current_freshness(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "CURRENT"
        and isinstance(node.value, ast.Name)
        and node.value.id == "EvidenceFreshness"
    )


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
