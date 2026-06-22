from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

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
BASELINE_OPERATIONS = {
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
    ("GET", "/metadata"),
}
BOUNDARY_TERMS = ("Gateway", "Workbench", "supported-feature promotion")
CAPABILITY_PATTERN = re.compile(r"\bidea\.[a-z0-9.-]+\b")
TEST_REFERENCE_PATTERN = re.compile(r"^(?P<path>tests/.+\.py)::(?P<test>[A-Za-z_][A-Za-z0-9_]*)$")
OPERATION_EVENT_TEST_TERMS = ("operation_event", "operation_events")


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


def _parse_json_examples(
    *,
    operation: tuple[str, str],
    field: str,
    examples: Any,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(examples, list) or not examples:
        return [f"{operation}: {field} must be a non-empty list"]
    for index, example in enumerate(examples):
        if not isinstance(example, str) or not example.strip():
            errors.append(f"{operation}: {field}[{index}] must be a non-empty string")
            continue
        stripped = example.strip()
        if stripped[0] not in "{[":
            continue
        try:
            json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(f"{operation}: {field}[{index}] must be valid JSON: {exc.msg}")
    return errors


def _validate_test_reference(operation: tuple[str, str], reference: str) -> list[str]:
    match = TEST_REFERENCE_PATTERN.match(reference)
    if not match:
        return [f"{operation}: test_evidence reference must use tests/path.py::test_name"]
    test_path = Path(match.group("path"))
    full_path = ROOT / test_path
    if not full_path.exists():
        return [f"{operation}: test_evidence file does not exist: {test_path.as_posix()}"]
    test_name = match.group("test")
    try:
        tree = ast.parse(full_path.read_text(encoding="utf-8"), filename=str(full_path))
    except SyntaxError:
        return [f"{operation}: test_evidence file is not parseable: {test_path.as_posix()}"]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
            return []
    return [f"{operation}: test_evidence test does not exist: {reference}"]


def _validate_certified_endpoint_posture(endpoint: dict[str, Any]) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if endpoint["certification_status"] != "certified":
        return []

    errors: list[str] = []
    if operation in BASELINE_OPERATIONS:
        errors.append(f"{operation}: baseline operation must not use certified status")

    combined_evidence_text = " ".join(
        [
            str(endpoint.get("when_to_use", "")),
            str(endpoint.get("when_not_to_use", "")),
            " ".join(str(example) for example in endpoint.get("error_examples", [])),
        ]
    )
    if not CAPABILITY_PATTERN.search(combined_evidence_text):
        errors.append(f"{operation}: certified endpoint must name at least one idea.* capability")

    unsupported_boundary = str(endpoint.get("when_not_to_use", ""))
    for boundary_term in BOUNDARY_TERMS:
        if boundary_term not in unsupported_boundary:
            errors.append(
                f"{operation}: when_not_to_use must explicitly preserve `{boundary_term}` boundary"
            )

    if "scripts/openapi_quality_gate.py" not in str(endpoint.get("openapi_evidence", "")):
        errors.append(
            f"{operation}: openapi_evidence must reference scripts/openapi_quality_gate.py"
        )

    if not any("403" in str(example) for example in endpoint.get("error_examples", [])):
        errors.append(f"{operation}: certified endpoint must document product-safe 403 behavior")

    test_evidence = endpoint.get("test_evidence", [])
    if not any(
        term in str(reference) for reference in test_evidence for term in OPERATION_EVENT_TEST_TERMS
    ):
        errors.append(
            f"{operation}: certified endpoint must reference bounded operation-event test evidence"
        )

    return errors


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

        errors.extend(
            _parse_json_examples(
                operation=operation,
                field="request_examples",
                examples=endpoint.get("request_examples"),
            )
        )
        errors.extend(
            _parse_json_examples(
                operation=operation,
                field="response_examples",
                examples=endpoint.get("response_examples"),
            )
        )
        for field in ("error_examples", "test_evidence"):
            value = endpoint.get(field)
            if not isinstance(value, list) or not value:
                errors.append(f"{operation}: {field} must be a non-empty list")

        for reference in endpoint.get("test_evidence", []):
            if isinstance(reference, str):
                errors.extend(_validate_test_reference(operation, reference))

        if (
            operation in BASELINE_OPERATIONS
            and endpoint["certification_status"] != "baseline_certified"
        ):
            errors.append(f"{operation}: baseline endpoint must use baseline_certified status")

        errors.extend(_validate_certified_endpoint_posture(endpoint))

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
