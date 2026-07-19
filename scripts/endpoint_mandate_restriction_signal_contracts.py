# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


MANDATE_RESTRICTION_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/mandate-restriction/evaluate",
)
MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/mandate-restriction/evaluate-from-source",
)
MANDATE_RESTRICTION_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_api_returns_review_candidate"
)
MANDATE_RESTRICTION_CALLER_BLOCKED_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_api_reports_stale_source_blocker"
)
MANDATE_RESTRICTION_CALLER_NON_CANDIDATE_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_api_exposes_non_candidate_success_modes"
)
MANDATE_RESTRICTION_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_from_source_api_returns_review_candidate"
)
MANDATE_RESTRICTION_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_from_source_closes_runtime_on_source_blocker"
)
MANDATE_RESTRICTION_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_mandate_restriction_signal_api.py::"
    "test_mandate_restriction_signal_from_source_exposes_non_candidate_success_modes"
)
MANDATE_RESTRICTION_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_mandate_restriction_signal_examples.py::"
    "test_mandate_restriction_examples_match_ledger_and_generated_openapi"
)


def validate_mandate_restriction_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.mandate_restriction_signal import (
        build_mandate_restriction_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MANDATE_RESTRICTION_EVALUATE_OPERATION,
        expected=build_mandate_restriction_evaluation_response_examples(),
        workflow_name="mandate-restriction-evaluation",
        required_test_evidence=(
            (
                MANDATE_RESTRICTION_CALLER_CANDIDATE_TEST,
                "candidate-created HTTP behavior test",
            ),
            (MANDATE_RESTRICTION_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (
                MANDATE_RESTRICTION_CALLER_NON_CANDIDATE_TEST,
                "suppressed and not-eligible HTTP behavior test",
            ),
            (
                MANDATE_RESTRICTION_SUCCESS_CONTRACT_TEST,
                "complete mandate-restriction success publication contract test",
            ),
        ),
    )


def validate_source_backed_mandate_restriction_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.mandate_restriction_signal import (
        build_source_backed_mandate_restriction_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_mandate_restriction_evaluation_response_examples(),
        workflow_name="source-backed-mandate-restriction-evaluation",
        required_test_evidence=(
            (
                MANDATE_RESTRICTION_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (
                MANDATE_RESTRICTION_SOURCE_BLOCKED_TEST,
                "source-backed blocked behavior test",
            ),
            (
                MANDATE_RESTRICTION_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                MANDATE_RESTRICTION_SUCCESS_CONTRACT_TEST,
                "complete mandate-restriction success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_mandate_restriction_evaluation_success_contract",
    "validate_source_backed_mandate_restriction_evaluation_success_contract",
]
