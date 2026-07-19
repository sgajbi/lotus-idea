# ruff: noqa: E402
from __future__ import annotations

import ast
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.api.idempotency import REQUIRED_OPENAPI_IDEMPOTENCY_OPERATIONS  # noqa: E402

IDEMPOTENCY_VALIDATOR_NAMES = {"_validate_idempotency_key", "validate_idempotency_key"}


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def validate_api_idempotency_boundary(
    root: Path = ROOT,
    *,
    openapi_spec: Mapping[str, Any] | None = None,
) -> list[str]:
    api_dir = root / "src" / "app" / "api"
    allowed_module = api_dir / "idempotency.py"
    errors: list[str] = []
    for path in sorted(api_dir.glob("*.py")):
        if path == allowed_module:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in IDEMPOTENCY_VALIDATOR_NAMES:
                errors.append(
                    f"{_relative(path, root)}:{node.lineno}: API routes must use "
                    "`app.api.idempotency.validate_idempotency_key` instead of defining "
                    f"`{node.name}` locally"
                )
    if openapi_spec is not None:
        errors.extend(validate_openapi_idempotency_headers(openapi_spec))
    elif root == ROOT:
        errors.extend(validate_openapi_idempotency_headers(_current_openapi_spec()))
    return errors


def validate_openapi_idempotency_headers(openapi_spec: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    paths = openapi_spec.get("paths")
    if not isinstance(paths, Mapping):
        return ["OpenAPI spec missing paths object"]
    for method, path in REQUIRED_OPENAPI_IDEMPOTENCY_OPERATIONS:
        operation = _operation(paths, method, path)
        if operation is None:
            errors.append(f"{method.upper()} {path}: missing OpenAPI operation")
            continue
        parameter = _idempotency_parameter(operation)
        if parameter is None:
            errors.append(f"{method.upper()} {path}: missing Idempotency-Key OpenAPI header")
            continue
        if parameter.get("required") is not True:
            errors.append(
                f"{method.upper()} {path}: Idempotency-Key OpenAPI header must be required"
            )
        schema = parameter.get("schema")
        if isinstance(schema, Mapping) and "default" in schema:
            errors.append(
                f"{method.upper()} {path}: Idempotency-Key OpenAPI header must not publish "
                "a default value"
            )
    return errors


def _operation(paths: Mapping[str, Any], method: str, path: str) -> Mapping[str, Any] | None:
    path_item = paths.get(path)
    if not isinstance(path_item, Mapping):
        return None
    operation = path_item.get(method)
    return operation if isinstance(operation, Mapping) else None


def _idempotency_parameter(operation: Mapping[str, Any]) -> Mapping[str, Any] | None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return None
    for parameter in parameters:
        if not isinstance(parameter, Mapping):
            continue
        if parameter.get("name") == "Idempotency-Key" and parameter.get("in") == "header":
            return parameter
    return None


def _current_openapi_spec() -> Mapping[str, Any]:
    from app.main import app

    return app.openapi()


def main() -> int:
    errors = validate_api_idempotency_boundary()
    if errors:
        print("API idempotency boundary gate failed:")
        print("\n".join(errors))
        return 1
    print("API idempotency boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
