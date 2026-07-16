from __future__ import annotations

from typing import Any

from endpoint_contract_support import json_object_examples, openapi_operation


REVIEW_ACTION_OPERATION = ("POST", "/api/v1/idea-candidates/{candidateId}/review-actions")
FEEDBACK_OPERATION = ("POST", "/api/v1/idea-candidates/{candidateId}/feedback")
REVIEW_ACTION_IDENTITY_REPLAY_TEST = (
    "tests/integration/test_review_identity_api.py::"
    "test_review_action_api_governs_resource_identity_across_transport_keys"
)
FEEDBACK_IDENTITY_REPLAY_TEST = (
    "tests/integration/test_review_identity_api.py::"
    "test_feedback_api_governs_resource_identity_across_transport_keys"
)
REVIEW_ACTION_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_review_workflow.py::"
    "test_review_action_success_examples_match_ledger_and_openapi"
)
FEEDBACK_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_review_workflow.py::"
    "test_feedback_success_examples_match_ledger_and_openapi"
)


def validate_review_action_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.review_workflow import build_review_action_response_examples

    return _validate_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=REVIEW_ACTION_OPERATION,
        expected=build_review_action_response_examples(),
        workflow_name="review-action",
        replay_test=REVIEW_ACTION_IDENTITY_REPLAY_TEST,
        success_contract_test=REVIEW_ACTION_SUCCESS_CONTRACT_TEST,
    )


def validate_feedback_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.review_workflow import build_feedback_response_examples

    return _validate_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=FEEDBACK_OPERATION,
        expected=build_feedback_response_examples(),
        workflow_name="feedback",
        replay_test=FEEDBACK_IDENTITY_REPLAY_TEST,
        success_contract_test=FEEDBACK_SUCCESS_CONTRACT_TEST,
    )


def _validate_success_contract(
    *,
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None,
    operation: tuple[str, str],
    expected: dict[str, dict[str, Any]],
    workflow_name: str,
    replay_test: str,
    success_contract_test: str,
) -> list[str]:
    endpoint_operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if endpoint_operation != operation:
        return []

    errors: list[str] = []
    if json_object_examples(endpoint.get("response_examples")) != tuple(expected.values()):
        errors.append(
            f"{operation}: response_examples must exactly match every code-owned {workflow_name} "
            "success mode"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    if replay_test not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the cross-key {workflow_name} replay "
            "integration test"
        )
    if success_contract_test not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the complete {workflow_name} success "
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
                f"code-owned {workflow_name} success mode"
            )

    return errors


__all__ = [
    "validate_feedback_success_contract",
    "validate_review_action_success_contract",
]
