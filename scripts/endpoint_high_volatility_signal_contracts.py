from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


HIGH_VOLATILITY_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/high-volatility/evaluate",
)
HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/high-volatility/evaluate-from-source",
)
HIGH_VOLATILITY_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_api_returns_review_candidate"
)
HIGH_VOLATILITY_CALLER_BLOCKED_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_api_reports_stale_source_blocker"
)
HIGH_VOLATILITY_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_api_reports_duplicate_suppressed"
)
HIGH_VOLATILITY_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_api_reports_below_threshold_not_eligible"
)
HIGH_VOLATILITY_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_from_source_api_returns_review_candidate"
)
HIGH_VOLATILITY_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_from_source_closes_runtime_on_source_blocker"
)
HIGH_VOLATILITY_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_high_volatility_signal_api.py::"
    "test_high_volatility_signal_from_source_exposes_non_candidate_success_modes"
)
HIGH_VOLATILITY_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_high_volatility_signal_examples.py::"
    "test_high_volatility_examples_match_ledger_and_generated_openapi"
)


def validate_high_volatility_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.high_volatility_signal import (
        build_high_volatility_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HIGH_VOLATILITY_EVALUATE_OPERATION,
        expected=build_high_volatility_evaluation_response_examples(),
        workflow_name="high-volatility-evaluation",
        required_test_evidence=(
            (HIGH_VOLATILITY_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (HIGH_VOLATILITY_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (HIGH_VOLATILITY_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (HIGH_VOLATILITY_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                HIGH_VOLATILITY_SUCCESS_CONTRACT_TEST,
                "complete high-volatility success publication contract test",
            ),
        ),
    )


def validate_source_backed_high_volatility_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.high_volatility_signal import (
        build_source_backed_high_volatility_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_high_volatility_evaluation_response_examples(),
        workflow_name="source-backed-high-volatility-evaluation",
        required_test_evidence=(
            (
                HIGH_VOLATILITY_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (HIGH_VOLATILITY_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                HIGH_VOLATILITY_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                HIGH_VOLATILITY_SUCCESS_CONTRACT_TEST,
                "complete high-volatility success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_high_volatility_evaluation_success_contract",
    "validate_source_backed_high_volatility_evaluation_success_contract",
]
