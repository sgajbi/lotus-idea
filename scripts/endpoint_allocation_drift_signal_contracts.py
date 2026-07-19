# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


ALLOCATION_DRIFT_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/allocation-drift/evaluate",
)
ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/allocation-drift/evaluate-from-source",
)
ALLOCATION_DRIFT_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_api_returns_pm_review_candidate"
)
ALLOCATION_DRIFT_CALLER_BLOCKED_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_api_reports_stale_source_blocker"
)
ALLOCATION_DRIFT_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_api_reports_duplicate_suppressed"
)
ALLOCATION_DRIFT_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_api_reports_below_threshold_not_eligible"
)
ALLOCATION_DRIFT_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_from_source_api_returns_pm_review_candidate"
)
ALLOCATION_DRIFT_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_from_source_closes_runtime_on_source_blocker"
)
ALLOCATION_DRIFT_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_allocation_drift_signal_api.py::"
    "test_allocation_drift_signal_from_source_exposes_non_candidate_success_modes"
)
ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_allocation_drift_signal_examples.py::"
    "test_allocation_drift_examples_match_ledger_and_generated_openapi"
)


def validate_allocation_drift_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.allocation_drift_signal import (
        build_allocation_drift_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=ALLOCATION_DRIFT_EVALUATE_OPERATION,
        expected=build_allocation_drift_evaluation_response_examples(),
        workflow_name="allocation-drift-evaluation",
        required_test_evidence=(
            (ALLOCATION_DRIFT_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (ALLOCATION_DRIFT_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (ALLOCATION_DRIFT_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (ALLOCATION_DRIFT_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST,
                "complete allocation-drift success publication contract test",
            ),
        ),
    )


def validate_source_backed_allocation_drift_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.allocation_drift_signal import (
        build_source_backed_allocation_drift_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_allocation_drift_evaluation_response_examples(),
        workflow_name="source-backed-allocation-drift-evaluation",
        required_test_evidence=(
            (
                ALLOCATION_DRIFT_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (ALLOCATION_DRIFT_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                ALLOCATION_DRIFT_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST,
                "complete allocation-drift success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_allocation_drift_evaluation_success_contract",
    "validate_source_backed_allocation_drift_evaluation_success_contract",
]
