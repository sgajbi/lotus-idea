from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


CONVERSION_INTENT_OPERATION = (
    "POST",
    "/api/v1/idea-candidates/{candidateId}/conversion-intents",
)
CONVERSION_OUTCOME_OPERATION = (
    "POST",
    "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
)
CONVERSION_INTENT_REPLAY_TEST = (
    "tests/integration/test_review_workflow_api.py::"
    "test_conversion_intent_api_replays_and_conflicts_idempotently"
)
CONVERSION_OUTCOME_REPLAY_TEST = (
    "tests/integration/test_conversion_outcome_lifecycle_api.py::"
    "test_conversion_outcome_api_replays_identity_and_rejects_changed_source_fact"
)
CONVERSION_INTENT_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_conversion_workflow.py::"
    "test_conversion_intent_success_examples_match_ledger_and_openapi"
)
CONVERSION_OUTCOME_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_conversion_workflow.py::"
    "test_conversion_outcome_success_examples_match_ledger_and_openapi"
)


def validate_conversion_intent_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.conversion_workflow import (
        build_conversion_intent_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CONVERSION_INTENT_OPERATION,
        expected=build_conversion_intent_response_examples(),
        workflow_name="conversion-intent",
        replay_test=CONVERSION_INTENT_REPLAY_TEST,
        replay_evidence_description="idempotent conversion-intent replay integration test",
        success_contract_test=CONVERSION_INTENT_SUCCESS_CONTRACT_TEST,
    )


def validate_conversion_outcome_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.conversion_workflow import (
        build_conversion_outcome_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CONVERSION_OUTCOME_OPERATION,
        expected=build_conversion_outcome_response_examples(),
        workflow_name="conversion-outcome",
        replay_test=CONVERSION_OUTCOME_REPLAY_TEST,
        replay_evidence_description="cross-key conversion-outcome replay integration test",
        success_contract_test=CONVERSION_OUTCOME_SUCCESS_CONTRACT_TEST,
    )


__all__ = [
    "validate_conversion_intent_success_contract",
    "validate_conversion_outcome_success_contract",
]
