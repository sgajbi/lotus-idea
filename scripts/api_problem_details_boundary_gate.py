from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "src" / "app" / "api"
API_ENTRYPOINTS = (ROOT / "src" / "app" / "main.py",)
ALLOWED_DIRECT_ERROR_IMPORTS = {API_DIR / "problem_details.py"}


def validate_api_problem_details_boundary() -> list[str]:
    errors: list[str] = []
    for path in sorted((*API_DIR.glob("*.py"), *API_ENTRYPOINTS)):
        if path in ALLOWED_DIRECT_ERROR_IMPORTS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.errors":
                imported_names = ", ".join(alias.name for alias in node.names)
                relative_path = path.relative_to(ROOT).as_posix()
                errors.append(
                    f"{relative_path}:{node.lineno}: import {imported_names} "
                    "through app.api.problem_details, not app.errors"
                )
    return errors


def main() -> int:
    errors = validate_api_problem_details_boundary()
    if errors:
        print("API ProblemDetails boundary gate failed:")
        print("\n".join(errors))
        return 1
    print("API ProblemDetails boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
