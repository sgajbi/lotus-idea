# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


BOND_MATURITY_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/bond-maturity/evaluate",
)
BOND_MATURITY_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
)
BOND_MATURITY_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_signal_api_returns_review_candidate"
)
BOND_MATURITY_CALLER_BLOCKED_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_signal_api_reports_stale_source_blocker"
)
BOND_MATURITY_CALLER_SUPPRESSED_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_signal_api_reports_duplicate_suppressed"
)
BOND_MATURITY_CALLER_NOT_ELIGIBLE_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_signal_api_reports_outside_window_not_eligible"
)
BOND_MATURITY_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_source_api_fetches_core_evidence_without_persistence"
)
BOND_MATURITY_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_source_api_returns_blocked_posture_for_core_unavailable"
)
BOND_MATURITY_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_bond_maturity_signal_api.py::"
    "test_bond_maturity_source_api_exposes_non_candidate_success_modes"
)
BOND_MATURITY_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_bond_maturity_signal_examples.py::"
    "test_bond_maturity_examples_match_ledger_and_generated_openapi"
)


def validate_bond_maturity_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.bond_maturity_signal import (
        build_bond_maturity_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=BOND_MATURITY_EVALUATE_OPERATION,
        expected=build_bond_maturity_evaluation_response_examples(),
        workflow_name="bond-maturity-evaluation",
        required_test_evidence=(
            (BOND_MATURITY_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (BOND_MATURITY_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (BOND_MATURITY_CALLER_SUPPRESSED_TEST, "suppressed HTTP behavior test"),
            (BOND_MATURITY_CALLER_NOT_ELIGIBLE_TEST, "not-eligible HTTP behavior test"),
            (
                BOND_MATURITY_SUCCESS_CONTRACT_TEST,
                "complete bond-maturity success publication contract test",
            ),
        ),
    )


def validate_source_backed_bond_maturity_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.bond_maturity_signal import (
        build_source_backed_bond_maturity_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=BOND_MATURITY_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_bond_maturity_evaluation_response_examples(),
        workflow_name="source-backed-bond-maturity-evaluation",
        required_test_evidence=(
            (BOND_MATURITY_SOURCE_CANDIDATE_TEST, "source-backed candidate-created behavior test"),
            (BOND_MATURITY_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                BOND_MATURITY_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                BOND_MATURITY_SUCCESS_CONTRACT_TEST,
                "complete bond-maturity success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_bond_maturity_evaluation_success_contract",
    "validate_source_backed_bond_maturity_evaluation_success_contract",
]
