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


def _base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def _is_typed_dict_definition(node: ast.ClassDef) -> bool:
    return any(_base_name(base) == "TypedDict" for base in node.bases)


def validate_api_route_metadata(root: Path = ROOT) -> list[str]:
    api_root = root / "src" / "app" / "api"
    shared_module = api_root / "route_metadata.py"
    errors: list[str] = []
    for path in sorted(api_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name not in {"RouteMetadata", "SignalRouteMetadata"}:
                continue
            if not _is_typed_dict_definition(node):
                continue
            if path == shared_module and node.name == "RouteMetadata":
                continue
            errors.append(
                f"{_relative(path, root)}:{node.lineno}: route metadata TypedDict must be "
                "defined once in `app.api.route_metadata`"
            )
    return errors


def main() -> int:
    errors = validate_api_route_metadata()
    if errors:
        print("API route metadata gate failed:")
        print("\n".join(errors))
        return 1
    print("API route metadata gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
