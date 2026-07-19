# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


MISSING_RISK_PROFILE_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/missing-risk-profile/evaluate",
)
MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/missing-risk-profile/evaluate-from-source",
)
MISSING_RISK_PROFILE_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_api_returns_review_candidate"
)
MISSING_RISK_PROFILE_CALLER_BLOCKED_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_api_reports_stale_source_blocker"
)
MISSING_RISK_PROFILE_CALLER_NON_CANDIDATE_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_api_exposes_non_candidate_success_modes"
)
MISSING_RISK_PROFILE_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_from_source_api_returns_review_candidate"
)
MISSING_RISK_PROFILE_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_from_source_closes_runtime_on_source_blocker"
)
MISSING_RISK_PROFILE_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_missing_risk_profile_signal_api.py::"
    "test_missing_risk_profile_signal_from_source_exposes_non_candidate_success_modes"
)
MISSING_RISK_PROFILE_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_missing_risk_profile_signal_examples.py::"
    "test_missing_risk_profile_examples_match_ledger_and_generated_openapi"
)


def validate_missing_risk_profile_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.missing_risk_profile_signal import (
        build_missing_risk_profile_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MISSING_RISK_PROFILE_EVALUATE_OPERATION,
        expected=build_missing_risk_profile_evaluation_response_examples(),
        workflow_name="missing-risk-profile-evaluation",
        required_test_evidence=(
            (
                MISSING_RISK_PROFILE_CALLER_CANDIDATE_TEST,
                "candidate-created HTTP behavior test",
            ),
            (MISSING_RISK_PROFILE_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (
                MISSING_RISK_PROFILE_CALLER_NON_CANDIDATE_TEST,
                "suppressed and not-eligible HTTP behavior test",
            ),
            (
                MISSING_RISK_PROFILE_SUCCESS_CONTRACT_TEST,
                "complete missing-risk-profile success publication contract test",
            ),
        ),
    )


def validate_source_backed_missing_risk_profile_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.missing_risk_profile_signal import (
        build_source_backed_missing_risk_profile_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_missing_risk_profile_evaluation_response_examples(),
        workflow_name="source-backed-missing-risk-profile-evaluation",
        required_test_evidence=(
            (
                MISSING_RISK_PROFILE_SOURCE_CANDIDATE_TEST,
                "source-backed candidate-created behavior test",
            ),
            (
                MISSING_RISK_PROFILE_SOURCE_BLOCKED_TEST,
                "source-backed blocked behavior test",
            ),
            (
                MISSING_RISK_PROFILE_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                MISSING_RISK_PROFILE_SUCCESS_CONTRACT_TEST,
                "complete missing-risk-profile success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_missing_risk_profile_evaluation_success_contract",
    "validate_source_backed_missing_risk_profile_evaluation_success_contract",
]
