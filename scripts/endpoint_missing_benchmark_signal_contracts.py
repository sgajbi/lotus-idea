from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


MISSING_BENCHMARK_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/missing-benchmark/evaluate",
)
MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
)
MISSING_BENCHMARK_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_signal_api_returns_review_candidate"
)
MISSING_BENCHMARK_CALLER_BLOCKED_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_signal_api_reports_stale_source_blocker"
)
MISSING_BENCHMARK_CALLER_NON_CANDIDATE_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_signal_api_exposes_non_candidate_success_modes"
)
MISSING_BENCHMARK_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_source_api_fetches_core_evidence_without_persistence"
)
MISSING_BENCHMARK_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_source_api_returns_blocked_posture_for_core_unavailable"
)
MISSING_BENCHMARK_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_missing_benchmark_signal_api.py::"
    "test_missing_benchmark_source_api_exposes_non_candidate_success_modes"
)
MISSING_BENCHMARK_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_missing_benchmark_signal_examples.py::"
    "test_missing_benchmark_examples_match_ledger_and_generated_openapi"
)


def validate_missing_benchmark_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.missing_benchmark_signal import (
        build_missing_benchmark_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MISSING_BENCHMARK_EVALUATE_OPERATION,
        expected=build_missing_benchmark_evaluation_response_examples(),
        workflow_name="missing-benchmark-evaluation",
        required_test_evidence=(
            (MISSING_BENCHMARK_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (MISSING_BENCHMARK_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (
                MISSING_BENCHMARK_CALLER_NON_CANDIDATE_TEST,
                "suppressed and not-eligible HTTP behavior test",
            ),
            (
                MISSING_BENCHMARK_SUCCESS_CONTRACT_TEST,
                "complete missing-benchmark success publication contract test",
            ),
        ),
    )


def validate_source_backed_missing_benchmark_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.missing_benchmark_signal import (
        build_source_backed_missing_benchmark_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MISSING_BENCHMARK_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_missing_benchmark_evaluation_response_examples(),
        workflow_name="source-backed-missing-benchmark-evaluation",
        required_test_evidence=(
            (
                MISSING_BENCHMARK_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (
                MISSING_BENCHMARK_SOURCE_BLOCKED_TEST,
                "source-backed blocked behavior test",
            ),
            (
                MISSING_BENCHMARK_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                MISSING_BENCHMARK_SUCCESS_CONTRACT_TEST,
                "complete missing-benchmark success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_missing_benchmark_evaluation_success_contract",
    "validate_source_backed_missing_benchmark_evaluation_success_contract",
]
