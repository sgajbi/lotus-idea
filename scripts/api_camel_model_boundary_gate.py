from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_true_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_populate_by_name_config(node: ast.Call) -> bool:
    if _call_name(node.func) != "ConfigDict":
        return False
    return any(
        keyword.arg == "populate_by_name" and _is_true_constant(keyword.value)
        for keyword in node.keywords
    )


def validate_api_camel_model_boundary(root: Path = ROOT) -> list[str]:
    api_dir = root / "src" / "app" / "api"
    allowed_module = api_dir / "base_model.py"
    errors: list[str] = []
    for path in sorted(api_dir.glob("*.py")):
        if path == allowed_module:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "CamelModel":
                errors.append(
                    f"{_relative(path, root)}:{node.lineno}: API DTO camel-case model "
                    "configuration must be defined once in `app.api.base_model.CamelModel`"
                )
            if isinstance(node, ast.Call) and _is_populate_by_name_config(node):
                errors.append(
                    f"{_relative(path, root)}:{node.lineno}: API DTO model alias configuration "
                    "must use `app.api.base_model.CamelModel` instead of local ConfigDict"
                )
    return errors


def main() -> int:
    errors = validate_api_camel_model_boundary()
    if errors:
        print("API CamelModel boundary gate failed:")
        print("\n".join(errors))
        return 1
    print("API CamelModel boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
