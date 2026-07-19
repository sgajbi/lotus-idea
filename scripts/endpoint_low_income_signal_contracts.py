# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


LOW_INCOME_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/low-income/evaluate",
)
LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/low-income/evaluate-from-source",
)
LOW_INCOME_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_signal_api_returns_review_candidate"
)
LOW_INCOME_CALLER_BLOCKED_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_signal_api_reports_stale_source_blocker"
)
LOW_INCOME_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_signal_api_reports_duplicate_suppressed"
)
LOW_INCOME_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_signal_api_reports_above_threshold_not_eligible"
)
LOW_INCOME_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_source_api_fetches_core_evidence_without_persistence"
)
LOW_INCOME_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_source_api_returns_blocked_posture_for_core_unavailable"
)
LOW_INCOME_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_low_income_signal_api.py::"
    "test_low_income_source_api_exposes_suppressed_and_not_eligible_success_modes"
)
LOW_INCOME_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_low_income_signal_examples.py::"
    "test_low_income_examples_match_ledger_and_generated_openapi"
)


def validate_low_income_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.low_income_signal import (
        build_low_income_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=LOW_INCOME_EVALUATE_OPERATION,
        expected=build_low_income_evaluation_response_examples(),
        workflow_name="low-income-evaluation",
        required_test_evidence=(
            (LOW_INCOME_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (LOW_INCOME_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (LOW_INCOME_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (LOW_INCOME_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                LOW_INCOME_SUCCESS_CONTRACT_TEST,
                "complete low-income success publication contract test",
            ),
        ),
    )


def validate_source_backed_low_income_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.low_income_signal import (
        build_source_backed_low_income_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_low_income_evaluation_response_examples(),
        workflow_name="source-backed-low-income-evaluation",
        required_test_evidence=(
            (LOW_INCOME_SOURCE_CANDIDATE_TEST, "source-backed candidate-created behavior test"),
            (LOW_INCOME_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                LOW_INCOME_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                LOW_INCOME_SUCCESS_CONTRACT_TEST,
                "complete low-income success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_low_income_evaluation_success_contract",
    "validate_source_backed_low_income_evaluation_success_contract",
]
