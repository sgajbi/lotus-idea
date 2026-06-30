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


def validate_api_temporal_validation_boundary(root: Path = ROOT) -> list[str]:
    api_dir = root / "src" / "app" / "api"
    allowed_module = root / "src" / "app" / "api" / "temporal_validation.py"
    errors: list[str] = []
    for path in sorted(api_dir.glob("*.py")):
        if path == allowed_module:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "tzinfo":
                errors.append(
                    f"{_relative(path, root)}:{node.lineno}: API routes must use "
                    "`app.api.temporal_validation` instead of checking `tzinfo` directly"
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "utcoffset":
                    errors.append(
                        f"{_relative(path, root)}:{node.lineno}: API routes must use "
                        "`app.api.temporal_validation` instead of calling `utcoffset()` directly"
                    )
    return errors


def main() -> int:
    errors = validate_api_temporal_validation_boundary()
    if errors:
        print("API temporal validation boundary gate failed:")
        print("\n".join(errors))
        return 1
    print("API temporal validation boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
