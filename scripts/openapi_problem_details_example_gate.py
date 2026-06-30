from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from app.main import app  # noqa: E402


def _problem_details_schema(schema: dict[str, Any]) -> bool:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.endswith("/ProblemDetails"):
        return True
    return any(
        _problem_details_schema(value) for value in schema.values() if isinstance(value, dict)
    )


def validate_problem_details_examples() -> list[str]:
    errors: list[str] = []
    openapi = app.openapi()
    for path, methods in sorted(openapi["paths"].items()):
        for method, operation in sorted(methods.items()):
            for status_code, response in sorted(operation.get("responses", {}).items()):
                content = response.get("content", {}).get("application/json", {})
                schema = content.get("schema", {})
                if not isinstance(schema, dict) or not _problem_details_schema(schema):
                    continue
                if "example" in content or "examples" in content:
                    continue
                errors.append(
                    f"{method.upper()} {path} {status_code}: ProblemDetails response "
                    "must include an OpenAPI example"
                )
    return errors


def main() -> int:
    errors = validate_problem_details_examples()
    if errors:
        print("OpenAPI ProblemDetails example gate failed:")
        print("\n".join(errors))
        return 1
    print("OpenAPI ProblemDetails example gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
