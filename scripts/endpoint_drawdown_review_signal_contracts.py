from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


DRAWDOWN_REVIEW_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/drawdown-review/evaluate",
)
DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/drawdown-review/evaluate-from-source",
)
DRAWDOWN_REVIEW_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_api_returns_review_candidate"
)
DRAWDOWN_REVIEW_CALLER_BLOCKED_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_api_reports_stale_source_blocker"
)
DRAWDOWN_REVIEW_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_api_reports_duplicate_suppressed"
)
DRAWDOWN_REVIEW_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_api_reports_below_threshold_not_eligible"
)
DRAWDOWN_REVIEW_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_from_source_api_returns_review_candidate"
)
DRAWDOWN_REVIEW_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_from_source_closes_runtime_on_source_blocker"
)
DRAWDOWN_REVIEW_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_drawdown_review_signal_api.py::"
    "test_drawdown_review_signal_from_source_exposes_non_candidate_success_modes"
)
DRAWDOWN_REVIEW_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_drawdown_review_signal_examples.py::"
    "test_drawdown_review_examples_match_ledger_and_generated_openapi"
)


def validate_drawdown_review_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.drawdown_review_signal import (
        build_drawdown_review_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=DRAWDOWN_REVIEW_EVALUATE_OPERATION,
        expected=build_drawdown_review_evaluation_response_examples(),
        workflow_name="drawdown-review-evaluation",
        required_test_evidence=(
            (DRAWDOWN_REVIEW_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (DRAWDOWN_REVIEW_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (DRAWDOWN_REVIEW_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (DRAWDOWN_REVIEW_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                DRAWDOWN_REVIEW_SUCCESS_CONTRACT_TEST,
                "complete drawdown-review success publication contract test",
            ),
        ),
    )


def validate_source_backed_drawdown_review_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.drawdown_review_signal import (
        build_source_backed_drawdown_review_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_drawdown_review_evaluation_response_examples(),
        workflow_name="source-backed-drawdown-review-evaluation",
        required_test_evidence=(
            (
                DRAWDOWN_REVIEW_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (DRAWDOWN_REVIEW_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                DRAWDOWN_REVIEW_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                DRAWDOWN_REVIEW_SUCCESS_CONTRACT_TEST,
                "complete drawdown-review success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_drawdown_review_evaluation_success_contract",
    "validate_source_backed_drawdown_review_evaluation_success_contract",
]
