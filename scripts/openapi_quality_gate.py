from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.main import app  # noqa: E402


def _operation_name(method: str, path: str) -> str:
    return f"{method.upper()} {path}"


def _has_example(response: dict) -> bool:
    content = response.get("content")
    if not isinstance(content, dict):
        return False
    for media in content.values():
        if not isinstance(media, dict):
            continue
        if "example" in media or "examples" in media:
            return True
    return False


def main() -> None:
    spec = app.openapi()
    if "paths" not in spec or not spec["paths"]:
        raise SystemExit("OpenAPI gate failed: no paths defined")
    errors: list[str] = []
    for path, path_item in spec["paths"].items():
        if not isinstance(path_item, dict):
            errors.append(f"{path}: path item must be an object")
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            name = _operation_name(method, path)
            if not operation.get("summary"):
                errors.append(f"{name}: missing summary")
            if not operation.get("description"):
                errors.append(f"{name}: missing description")
            if not operation.get("tags"):
                errors.append(f"{name}: missing tag")
            responses = operation.get("responses")
            if not isinstance(responses, dict) or not responses:
                errors.append(f"{name}: missing responses")
                continue
            success_responses = [
                response
                for status_code, response in responses.items()
                if str(status_code).startswith("2")
            ]
            if not success_responses:
                errors.append(f"{name}: missing 2xx response")
            for status_code, response in responses.items():
                if not isinstance(response, dict):
                    errors.append(f"{name}: response {status_code} must be an object")
                    continue
                if not response.get("description"):
                    errors.append(f"{name}: response {status_code} missing description")
            if not any(_has_example(response) for response in success_responses):
                errors.append(f"{name}: missing success response example")
    if errors:
        raise SystemExit("OpenAPI gate failed:\n" + "\n".join(sorted(errors)))
    print("OpenAPI gate passed")


if __name__ == "__main__":
    main()
