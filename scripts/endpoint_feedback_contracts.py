from __future__ import annotations

from typing import Any

from endpoint_contract_support import json_object_examples, openapi_operation


FEEDBACK_OPERATION = ("POST", "/api/v1/idea-candidates/{candidateId}/feedback")
FEEDBACK_IDENTITY_REPLAY_TEST = (
    "tests/integration/test_review_identity_api.py::"
    "test_feedback_api_governs_resource_identity_across_transport_keys"
)
FEEDBACK_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_feedback.py::"
    "test_feedback_success_examples_match_ledger_and_openapi"
)


def validate_feedback_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if operation != FEEDBACK_OPERATION:
        return []

    from app.api.examples.feedback import build_feedback_response_examples

    expected = build_feedback_response_examples()
    errors: list[str] = []
    if json_object_examples(endpoint.get("response_examples")) != tuple(expected.values()):
        errors.append(
            f"{operation}: response_examples must exactly match every code-owned feedback "
            "success mode"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    if FEEDBACK_IDENTITY_REPLAY_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the cross-key feedback replay integration test"
        )
    if FEEDBACK_SUCCESS_CONTRACT_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the complete feedback success "
            "publication contract test"
        )

    if openapi_spec is not None:
        operation_schema = openapi_operation(openapi_spec, operation)
        media = (
            operation_schema.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            if operation_schema is not None
            else {}
        )
        examples = media.get("examples", {}) if isinstance(media, dict) else {}
        published = {
            str(name): metadata.get("value")
            for name, metadata in examples.items()
            if isinstance(metadata, dict)
        }
        if published != expected:
            errors.append(
                f"{operation}: OpenAPI 200 examples must exactly match every named "
                "code-owned feedback success mode"
            )

    return errors


__all__ = ["validate_feedback_success_contract"]
