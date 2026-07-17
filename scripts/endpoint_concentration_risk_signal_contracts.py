from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


CONCENTRATION_RISK_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/concentration-risk/evaluate",
)
CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
)
CONCENTRATION_RISK_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_api_returns_review_candidate"
)
CONCENTRATION_RISK_CALLER_BLOCKED_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_api_reports_stale_source_blocker"
)
CONCENTRATION_RISK_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_api_reports_duplicate_suppressed"
)
CONCENTRATION_RISK_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_api_reports_below_threshold_not_eligible"
)
CONCENTRATION_RISK_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_from_source_api_returns_review_candidate"
)
CONCENTRATION_RISK_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_from_source_closes_runtime_on_source_blocker"
)
CONCENTRATION_RISK_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_concentration_risk_signal_api.py::"
    "test_concentration_risk_signal_from_source_exposes_non_candidate_success_modes"
)
CONCENTRATION_RISK_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_concentration_risk_signal_examples.py::"
    "test_concentration_risk_examples_match_ledger_and_generated_openapi"
)


def validate_concentration_risk_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.concentration_risk_signal import (
        build_concentration_risk_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CONCENTRATION_RISK_EVALUATE_OPERATION,
        expected=build_concentration_risk_evaluation_response_examples(),
        workflow_name="concentration-risk-evaluation",
        required_test_evidence=(
            (CONCENTRATION_RISK_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (CONCENTRATION_RISK_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (CONCENTRATION_RISK_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (CONCENTRATION_RISK_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                CONCENTRATION_RISK_SUCCESS_CONTRACT_TEST,
                "complete concentration-risk success publication contract test",
            ),
        ),
    )


def validate_source_backed_concentration_risk_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.concentration_risk_signal import (
        build_source_backed_concentration_risk_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_concentration_risk_evaluation_response_examples(),
        workflow_name="source-backed-concentration-risk-evaluation",
        required_test_evidence=(
            (
                CONCENTRATION_RISK_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (CONCENTRATION_RISK_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                CONCENTRATION_RISK_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                CONCENTRATION_RISK_SUCCESS_CONTRACT_TEST,
                "complete concentration-risk success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_concentration_risk_evaluation_success_contract",
    "validate_source_backed_concentration_risk_evaluation_success_contract",
]
