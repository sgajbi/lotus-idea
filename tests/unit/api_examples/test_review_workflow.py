from __future__ import annotations

import json
from pathlib import Path

from app.api.examples.review_workflow import (
    build_feedback_response_examples,
    build_review_action_response_examples,
)
from app.api.review_workflow_models import FeedbackResponse, ReviewActionResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
REVIEW_ACTION_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/review-actions"
FEEDBACK_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/feedback"


def test_review_action_success_examples_match_ledger_and_openapi() -> None:
    expected = build_review_action_response_examples()

    assert _ledger_examples(REVIEW_ACTION_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(REVIEW_ACTION_OPERATION_PATH) == expected
    assert all(ReviewActionResponse.model_validate(value) for value in expected.values())

    decision = expected["accepted"]["reviewDecision"]
    assert decision is not None
    assert decision["snoozedUntilUtc"] is None
    assert decision["grantsDownstreamAuthority"] is False
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["reviewDecision"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())


def test_feedback_success_examples_match_ledger_and_openapi() -> None:
    expected = build_feedback_response_examples()

    assert _ledger_examples(FEEDBACK_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(FEEDBACK_OPERATION_PATH) == expected
    assert all(FeedbackResponse.model_validate(value) for value in expected.values())

    assert expected["accepted"]["feedbackEvent"] is not None
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["feedbackEvent"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())


def _ledger_examples(operation_path: str) -> list[dict[str, object]]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == operation_path
    )
    return [json.loads(value) for value in endpoint["response_examples"]]


def _openapi_examples(operation_path: str) -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][operation_path]["post"]
    examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
