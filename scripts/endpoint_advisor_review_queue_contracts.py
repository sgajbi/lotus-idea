# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from typing import Any

from endpoint_contract_support import validate_named_success_contract


ADVISOR_REVIEW_QUEUE_OPERATION = ("GET", "/api/v1/review-queues/advisor")
ADVISOR_REVIEW_QUEUE_ITEMS_AVAILABLE_TEST = (
    "tests/integration/test_review_queue_api.py::"
    "test_advisor_review_queue_api_projects_persisted_candidates"
)
ADVISOR_REVIEW_QUEUE_EMPTY_TEST = (
    "tests/integration/test_review_queue_api.py::"
    "test_advisor_review_queue_api_returns_empty_queue_without_candidates"
)
ADVISOR_REVIEW_QUEUE_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_advisor_review_queue_examples.py::"
    "test_advisor_review_queue_examples_match_ledger_and_generated_openapi"
)


def validate_advisor_review_queue_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.advisor_review_queue import (
        build_advisor_review_queue_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=ADVISOR_REVIEW_QUEUE_OPERATION,
        expected=build_advisor_review_queue_response_examples(),
        workflow_name="advisor-review-queue",
        required_test_evidence=(
            (ADVISOR_REVIEW_QUEUE_ITEMS_AVAILABLE_TEST, "items-available HTTP behavior test"),
            (ADVISOR_REVIEW_QUEUE_EMPTY_TEST, "empty-queue HTTP behavior test"),
            (
                ADVISOR_REVIEW_QUEUE_SUCCESS_CONTRACT_TEST,
                "complete advisor-review-queue success publication contract test",
            ),
        ),
    )


__all__ = ["validate_advisor_review_queue_success_contract"]
