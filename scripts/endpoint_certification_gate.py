import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
APP_MAIN_PATH = Path("src/app/main.py")
REQUIRED_FIELDS = (
    "method",
    "path",
    "certification_status",
    "owner",
    "purpose",
    "when_to_use",
    "when_not_to_use",
    "request_examples",
    "response_examples",
    "error_examples",
    "test_evidence",
    "openapi_evidence",
)


def _openapi_operations_from_app() -> set[tuple[str, str]]:
    from app.main import app

    operations: set[tuple[str, str]] = set()
    for path, path_item in app.openapi().get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in path_item:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                operations.add((method.upper(), path))
    return operations


def _openapi_operations_from_source() -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    tree = ast.parse(APP_MAIN_PATH.read_text(encoding="utf-8"), filename=str(APP_MAIN_PATH))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            path = decorator.args[0].value
            if isinstance(path, str):
                operations.add((method.upper(), path))
    return operations


def _openapi_operations() -> set[tuple[str, str]]:
    try:
        return _openapi_operations_from_app()
    except ModuleNotFoundError as exc:
        if APP_MAIN_PATH.exists():
            return _openapi_operations_from_source()
        raise exc


def main() -> int:
    if not LEDGER_PATH.exists():
        print(f"Missing {LEDGER_PATH}")
        return 1

    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    if (
        payload.get("policy")
        != "Every public OpenAPI operation requires certification evidence before promotion."
    ):
        errors.append("endpoint certification policy must preserve evidence-backed promotion")

    entries = payload.get("endpoints")
    if not isinstance(entries, list):
        errors.append("endpoints must be a list")
        entries = []

    openapi_operations = _openapi_operations()
    ledger_operations: set[tuple[str, str]] = set()
    allowed_statuses = {"baseline_certified", "certified", "planned", "not_applicable"}

    for index, endpoint in enumerate(entries):
        if not isinstance(endpoint, dict):
            errors.append(f"endpoints[{index}] must be an object")
            continue

        missing = [field for field in REQUIRED_FIELDS if field not in endpoint]
        if missing:
            errors.append(f"endpoints[{index}] missing fields: {', '.join(missing)}")
            continue

        operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
        ledger_operations.add(operation)

        if endpoint["certification_status"] not in allowed_statuses:
            errors.append(
                f"{operation}: invalid certification_status {endpoint['certification_status']!r}"
            )

        for field in ("purpose", "when_to_use", "when_not_to_use", "owner", "openapi_evidence"):
            if not str(endpoint.get(field, "")).strip():
                errors.append(f"{operation}: {field} is required")

        for field in ("request_examples", "response_examples", "error_examples", "test_evidence"):
            value = endpoint.get(field)
            if not isinstance(value, list) or not value:
                errors.append(f"{operation}: {field} must be a non-empty list")

    missing_from_ledger = sorted(openapi_operations - ledger_operations)
    stale_in_ledger = sorted(ledger_operations - openapi_operations)

    for method, path in missing_from_ledger:
        errors.append(f"{method} {path}: missing endpoint certification ledger entry")
    for method, path in stale_in_ledger:
        errors.append(f"{method} {path}: stale endpoint certification ledger entry")

    if errors:
        print("\n".join(errors))
        return 1

    print("Endpoint certification gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
