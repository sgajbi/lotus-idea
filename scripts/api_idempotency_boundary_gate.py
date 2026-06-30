from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDEMPOTENCY_VALIDATOR_NAMES = {"_validate_idempotency_key", "validate_idempotency_key"}


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def validate_api_idempotency_boundary(root: Path = ROOT) -> list[str]:
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
    return errors


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
