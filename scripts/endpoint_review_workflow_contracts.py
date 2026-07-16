from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


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

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=REVIEW_ACTION_OPERATION,
        expected=build_review_action_response_examples(),
        workflow_name="review-action",
        required_test_evidence=(
            (
                REVIEW_ACTION_IDENTITY_REPLAY_TEST,
                "cross-key review-action replay integration test",
            ),
            (
                REVIEW_ACTION_SUCCESS_CONTRACT_TEST,
                "complete review-action success publication contract test",
            ),
        ),
    )


def validate_feedback_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.review_workflow import build_feedback_response_examples

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=FEEDBACK_OPERATION,
        expected=build_feedback_response_examples(),
        workflow_name="feedback",
        required_test_evidence=(
            (
                FEEDBACK_IDENTITY_REPLAY_TEST,
                "cross-key feedback replay integration test",
            ),
            (
                FEEDBACK_SUCCESS_CONTRACT_TEST,
                "complete feedback success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_feedback_success_contract",
    "validate_review_action_success_contract",
]
