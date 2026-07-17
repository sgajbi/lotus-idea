from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


UNDERPERFORMANCE_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/underperformance/evaluate",
)
UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/underperformance/evaluate-from-source",
)
UNDERPERFORMANCE_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_api_returns_review_candidate"
)
UNDERPERFORMANCE_CALLER_BLOCKED_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_api_reports_stale_source_blocker"
)
UNDERPERFORMANCE_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_api_reports_duplicate_suppressed"
)
UNDERPERFORMANCE_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_api_reports_above_threshold_not_eligible"
)
UNDERPERFORMANCE_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_from_source_api_returns_review_candidate"
)
UNDERPERFORMANCE_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_from_source_closes_runtime_on_source_blocker"
)
UNDERPERFORMANCE_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_underperformance_signal_api.py::"
    "test_underperformance_signal_from_source_exposes_non_candidate_success_modes"
)
UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_underperformance_signal_examples.py::"
    "test_underperformance_examples_match_ledger_and_generated_openapi"
)


def validate_underperformance_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.underperformance_signal import (
        build_underperformance_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=UNDERPERFORMANCE_EVALUATE_OPERATION,
        expected=build_underperformance_evaluation_response_examples(),
        workflow_name="underperformance-evaluation",
        required_test_evidence=(
            (UNDERPERFORMANCE_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (UNDERPERFORMANCE_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (UNDERPERFORMANCE_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (UNDERPERFORMANCE_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST,
                "complete underperformance success publication contract test",
            ),
        ),
    )


def validate_source_backed_underperformance_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.underperformance_signal import (
        build_source_backed_underperformance_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_underperformance_evaluation_response_examples(),
        workflow_name="source-backed-underperformance-evaluation",
        required_test_evidence=(
            (
                UNDERPERFORMANCE_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (UNDERPERFORMANCE_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                UNDERPERFORMANCE_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST,
                "complete underperformance success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_source_backed_underperformance_evaluation_success_contract",
    "validate_underperformance_evaluation_success_contract",
]
