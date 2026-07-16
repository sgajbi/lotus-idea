from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from endpoint_source_contracts import validate_signal_source_contract_error_examples  # noqa: E402
from endpoint_ai_contracts import (  # noqa: E402
    validate_ai_evaluation_success_contract,
    validate_ai_readiness_success_contract,
)
from endpoint_candidate_state_contracts import (  # noqa: E402
    validate_candidate_evidence_replay_success_contract,
    validate_candidate_lifecycle_success_contract,
)
from endpoint_review_workflow_contracts import (  # noqa: E402
    validate_feedback_success_contract,
    validate_review_action_success_contract,
)
from endpoint_report_evidence_contracts import (  # noqa: E402
    validate_report_evidence_pack_success_contract,
)
from endpoint_conversion_workflow_contracts import (  # noqa: E402
    validate_conversion_intent_success_contract,
    validate_conversion_outcome_success_contract,
)
from endpoint_contract_support import openapi_operation  # noqa: E402
from endpoint_status_contracts import validate_endpoint_status_contract  # noqa: E402

LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
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
CALLER_CONTEXT_EXTENSION = "x-lotus-caller-context"
CALLER_CONTEXT_SECURITY_SCHEME = "LotusCallerContext"
CALLER_CONTEXT_HEADERS_REQUIRING_DESCRIPTIONS = (
    "X-Caller-Capabilities",
    "X-Lotus-Trusted-Caller-Context",
)
TEST_REFERENCE_PATTERN = re.compile(r"^(?P<path>tests/.+\.py)::(?P<test>[A-Za-z_][A-Za-z0-9_]*)$")
ALLOWED_CERTIFICATION_STATUSES = frozenset(
    "baseline_certified certified implemented_not_certified planned not_applicable".split()
)
OPERATION_EVENT_TEST_TERMS = ("operation_event", "operation_events")
IMPLEMENTED_OPERATION_STATUSES = frozenset({"certified", "implemented_not_certified"})
NEGATIVE_OR_DEGRADED_TEST_TERMS = (
    "blocked",
    "conflict",
    "denied",
    "draining",
    "invalid",
    "not_found",
    "reject",
    "report",
    "require",
    "stale",
    "unavailable",
)
GATEWAY_PUBLICATION_ROUTES = {
    ("GET", "/api/v1/idea-candidates/{candidateId}"): (
        "GET /api/v1/ideas/candidates/{candidate_id}"
    ),
    ("GET", "/api/v1/review-queues/advisor"): ("GET /api/v1/ideas/review-queues/advisor"),
}
GATEWAY_PUBLICATION_CLAIM_TERMS = (
    "lotus-gateway",
    "Gateway publication",
    "/api/v1/ideas/",
)
GATEWAY_PUBLICATION_BOUNDARY_TERMS = (
    "Read-only Gateway publication",
    "lotus-gateway",
    "Workbench",
    "data-product certification",
    "client-ready publication",
    "supported-feature promotion",
)


def _openapi_schema_from_app() -> dict[str, Any]:
    from app.main import app

    return app.openapi()


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


def _validate_implemented_endpoint_posture(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if endpoint["certification_status"] not in IMPLEMENTED_OPERATION_STATUSES:
        return []

    errors: list[str] = []
    if endpoint["certification_status"] == "certified" and operation in BASELINE_OPERATIONS:
        errors.append(f"{operation}: baseline operation must not use certified status")

    capabilities = _capabilities_from_endpoint(endpoint)
    if not capabilities:
        errors.append(f"{operation}: implemented endpoint must name at least one idea.* capability")

    unsupported_boundary = str(endpoint.get("when_not_to_use", ""))
    for boundary_term in BOUNDARY_TERMS:
        if boundary_term not in unsupported_boundary:
            errors.append(
                f"{operation}: when_not_to_use must explicitly preserve `{boundary_term}` boundary"
            )

    if "scripts/openapi_quality_gate.py" not in str(endpoint.get("openapi_evidence", "")):
        errors.append(
            f"{operation}: implemented endpoint openapi_evidence must reference "
            "scripts/openapi_quality_gate.py"
        )

    if not any("403" in str(example) for example in endpoint.get("error_examples", [])):
        errors.append(f"{operation}: implemented endpoint must document product-safe 403 behavior")

    test_evidence = endpoint.get("test_evidence", [])
    if not any(
        term in str(reference) for reference in test_evidence for term in OPERATION_EVENT_TEST_TERMS
    ):
        errors.append(
            f"{operation}: implemented endpoint must reference bounded operation-event test evidence"
        )

    errors.extend(_validate_implemented_endpoint_test_pyramid(operation, test_evidence))
    errors.extend(_validate_gateway_publication_posture(endpoint))
    errors.extend(validate_ai_evaluation_success_contract(endpoint, openapi_spec))
    errors.extend(validate_ai_readiness_success_contract(endpoint, openapi_spec))
    errors.extend(validate_candidate_lifecycle_success_contract(endpoint, openapi_spec))
    errors.extend(validate_candidate_evidence_replay_success_contract(endpoint, openapi_spec))
    errors.extend(validate_conversion_intent_success_contract(endpoint, openapi_spec))
    errors.extend(validate_conversion_outcome_success_contract(endpoint, openapi_spec))
    errors.extend(validate_review_action_success_contract(endpoint, openapi_spec))
    errors.extend(validate_feedback_success_contract(endpoint, openapi_spec))
    errors.extend(validate_report_evidence_pack_success_contract(endpoint, openapi_spec))
    errors.extend(validate_signal_source_contract_error_examples(endpoint))
    errors.extend(validate_endpoint_status_contract(endpoint, openapi_spec))
    if openapi_spec is not None:
        errors.extend(_validate_openapi_caller_context_publication(endpoint, openapi_spec))

    return errors


def _capabilities_from_endpoint(endpoint: dict[str, Any]) -> tuple[str, ...]:
    combined_evidence_text = " ".join(
        [
            str(endpoint.get("when_to_use", "")),
            str(endpoint.get("when_not_to_use", "")),
            " ".join(str(example) for example in endpoint.get("error_examples", [])),
            " ".join(str(example) for example in endpoint.get("request_examples", [])),
        ]
    )
    return tuple(sorted(set(CAPABILITY_PATTERN.findall(combined_evidence_text))))


def _validate_openapi_caller_context_publication(
    endpoint: dict[str, Any], openapi_spec: dict[str, Any]
) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    capabilities = _capabilities_from_endpoint(endpoint)
    if not capabilities:
        return []

    operation_schema = openapi_operation(openapi_spec, operation)
    if operation_schema is None:
        return [f"{operation}: missing OpenAPI operation for caller-context publication"]

    errors: list[str] = []
    security = operation_schema.get("security")
    if not _security_names(security) or CALLER_CONTEXT_SECURITY_SCHEME not in _security_names(
        security
    ):
        errors.append(f"{operation}: OpenAPI must publish Lotus caller-context security")

    caller_context = operation_schema.get(CALLER_CONTEXT_EXTENSION)
    if not isinstance(caller_context, dict):
        return [
            *errors,
            f"{operation}: OpenAPI must publish `{CALLER_CONTEXT_EXTENSION}` requirements",
        ]

    published_capabilities = caller_context.get("requiredCapabilities")
    if not isinstance(published_capabilities, list) or any(
        capability not in published_capabilities for capability in capabilities
    ):
        errors.append(
            f"{operation}: OpenAPI caller-context requirements must include capabilities "
            f"{', '.join(capabilities)}"
        )

    if not str(caller_context.get("trustedCallerContextProvenance", "")).strip():
        errors.append(
            f"{operation}: OpenAPI caller-context requirements must describe trusted "
            "caller-context provenance"
        )

    errors.extend(_validate_caller_header_descriptions(operation, operation_schema))
    return errors


def _security_names(security: object) -> set[str]:
    names: set[str] = set()
    if not isinstance(security, list):
        return names
    for requirement in security:
        if isinstance(requirement, dict):
            names.update(str(name) for name in requirement)
    return names


def _validate_caller_header_descriptions(
    operation: tuple[str, str], operation_schema: dict[str, Any]
) -> list[str]:
    parameters = operation_schema.get("parameters")
    if not isinstance(parameters, list):
        return [f"{operation}: OpenAPI must publish caller-context header parameters"]

    descriptions: dict[str, str] = {}
    for parameter in parameters:
        if not isinstance(parameter, dict) or parameter.get("in") != "header":
            continue
        name = parameter.get("name")
        if isinstance(name, str):
            descriptions[name] = str(parameter.get("description", "")).strip()

    errors: list[str] = []
    for header_name in CALLER_CONTEXT_HEADERS_REQUIRING_DESCRIPTIONS:
        if not descriptions.get(header_name):
            errors.append(
                f"{operation}: OpenAPI caller-context header `{header_name}` must have a "
                "description"
            )
    return errors


def _validate_implemented_endpoint_test_pyramid(
    operation: tuple[str, str], test_evidence: object
) -> list[str]:
    if not isinstance(test_evidence, list):
        return [f"{operation}: implemented endpoint test_evidence must be a list"]

    references = [str(reference) for reference in test_evidence]
    errors: list[str] = []
    if not any(
        reference.startswith("tests/integration/")
        and not any(term in reference for term in OPERATION_EVENT_TEST_TERMS)
        for reference in references
    ):
        errors.append(
            f"{operation}: implemented endpoint must reference at least one integration API "
            "behavior test"
        )

    test_names = [
        reference.split("::", maxsplit=1)[1].lower()
        for reference in references
        if "::" in reference
    ]
    if not any(
        term in test_name for test_name in test_names for term in NEGATIVE_OR_DEGRADED_TEST_TERMS
    ):
        errors.append(
            f"{operation}: implemented endpoint must reference negative or degraded-path "
            "test evidence"
        )
    return errors


def _validate_gateway_publication_posture(endpoint: dict[str, Any]) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    unsupported_boundary = str(endpoint.get("when_not_to_use", ""))
    errors: list[str] = []

    claims_gateway_publication = any(
        term in unsupported_boundary for term in GATEWAY_PUBLICATION_CLAIM_TERMS
    )
    published_route = GATEWAY_PUBLICATION_ROUTES.get(operation)

    if claims_gateway_publication and published_route is None:
        errors.append(
            f"{operation}: only endpoints with implemented bounded Gateway publication may cite "
            "lotus-gateway publication"
        )

    if published_route is None:
        return errors

    if "Gateway contract" in unsupported_boundary:
        errors.append(
            f"{operation}: when_not_to_use must name the bounded read-only Gateway publication "
            "route instead of a generic Gateway contract denial"
        )

    for boundary_term in GATEWAY_PUBLICATION_BOUNDARY_TERMS:
        if boundary_term not in unsupported_boundary:
            errors.append(
                f"{operation}: Gateway publication boundary must include `{boundary_term}`"
            )

    if published_route not in unsupported_boundary:
        errors.append(f"{operation}: Gateway publication boundary must cite `{published_route}`")

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

    openapi_spec = _openapi_schema_from_app()
    openapi_operations = {
        (method, path)
        for path, path_item in openapi_spec.get("paths", {}).items()
        if isinstance(path_item, dict)
        for method in (method.upper() for method in path_item)
        if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    ledger_operations: set[tuple[str, str]] = set()
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

        if endpoint["certification_status"] not in ALLOWED_CERTIFICATION_STATUSES:
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

        errors.extend(_validate_implemented_endpoint_posture(endpoint, openapi_spec))

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
