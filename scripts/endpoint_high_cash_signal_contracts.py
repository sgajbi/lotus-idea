# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


HIGH_CASH_EVALUATE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/high-cash/evaluate",
)
HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION = (
    "POST",
    "/api/v1/idea-signals/high-cash/evaluate-from-source",
)
HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION = (
    "POST",
    "/api/v1/idea-signals/high-cash/evaluate-and-persist",
)
HIGH_CASH_CALLER_CANDIDATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_api_creates_candidate_from_source_owned_evidence"
)
HIGH_CASH_CALLER_BLOCKED_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_api_returns_blocked_posture_for_source_entitlement_denial"
)
HIGH_CASH_CALLER_NON_CANDIDATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_api_exposes_non_candidate_success_modes"
)
HIGH_CASH_SOURCE_CANDIDATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_source_api_fetches_core_evidence_without_persistence"
)
HIGH_CASH_SOURCE_BLOCKED_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_source_api_returns_blocked_posture_for_core_unavailable"
)
HIGH_CASH_SOURCE_NON_CANDIDATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_source_api_exposes_suppressed_and_not_eligible_success_modes"
)
HIGH_CASH_PERSIST_ACCEPTED_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_persist_api_persists_created_candidate_with_audit_posture"
)
HIGH_CASH_PERSIST_REPLAYED_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_persist_api_replays_same_idempotency_payload"
)
HIGH_CASH_PERSIST_DUPLICATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_persist_api_returns_existing_candidate_for_new_retry_key"
)
HIGH_CASH_PERSIST_BLOCKED_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_persist_api_does_not_persist_blocked_evaluation"
)
HIGH_CASH_PERSIST_NON_CANDIDATE_TEST = (
    "tests/integration/test_high_cash_signal_api.py::"
    "test_high_cash_persist_api_skips_non_candidate_success_modes"
)
HIGH_CASH_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_high_cash_signal_examples.py::"
    "test_high_cash_examples_match_ledger_and_generated_openapi"
)


def validate_high_cash_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.high_cash_signal import (
        build_high_cash_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HIGH_CASH_EVALUATE_OPERATION,
        expected=build_high_cash_evaluation_response_examples(),
        workflow_name="high-cash-evaluation",
        required_test_evidence=(
            (HIGH_CASH_CALLER_CANDIDATE_TEST, "candidate-created HTTP behavior test"),
            (HIGH_CASH_CALLER_BLOCKED_TEST, "blocked HTTP behavior test"),
            (
                HIGH_CASH_CALLER_NON_CANDIDATE_TEST,
                "suppressed and not-eligible HTTP behavior test",
            ),
            (
                HIGH_CASH_SUCCESS_CONTRACT_TEST,
                "complete high-cash success publication contract test",
            ),
        ),
    )


def validate_source_backed_high_cash_evaluation_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.high_cash_signal import (
        build_source_backed_high_cash_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION,
        expected=build_source_backed_high_cash_evaluation_response_examples(),
        workflow_name="source-backed-high-cash-evaluation",
        required_test_evidence=(
            (HIGH_CASH_SOURCE_CANDIDATE_TEST, "source-backed candidate-created behavior test"),
            (HIGH_CASH_SOURCE_BLOCKED_TEST, "source-backed blocked behavior test"),
            (
                HIGH_CASH_SOURCE_NON_CANDIDATE_TEST,
                "source-backed suppressed and not-eligible behavior test",
            ),
            (
                HIGH_CASH_SUCCESS_CONTRACT_TEST,
                "complete high-cash success publication contract test",
            ),
        ),
    )


def validate_high_cash_persistence_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.high_cash_signal import (
        build_high_cash_persistence_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION,
        expected=build_high_cash_persistence_response_examples(),
        workflow_name="high-cash-persistence",
        required_test_evidence=(
            (HIGH_CASH_PERSIST_ACCEPTED_TEST, "accepted candidate-persistence behavior test"),
            (HIGH_CASH_PERSIST_REPLAYED_TEST, "idempotent replay behavior test"),
            (HIGH_CASH_PERSIST_DUPLICATE_TEST, "duplicate-candidate behavior test"),
            (HIGH_CASH_PERSIST_BLOCKED_TEST, "blocked no-persistence behavior test"),
            (
                HIGH_CASH_PERSIST_NON_CANDIDATE_TEST,
                "suppressed and not-eligible no-persistence behavior test",
            ),
            (
                HIGH_CASH_SUCCESS_CONTRACT_TEST,
                "complete high-cash success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_high_cash_evaluation_success_contract",
    "validate_high_cash_persistence_success_contract",
    "validate_source_backed_high_cash_evaluation_success_contract",
]
