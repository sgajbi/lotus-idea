from __future__ import annotations

import json
from pathlib import Path

from app.api.examples.feedback import build_feedback_response_examples
from app.api.review_workflow_models import FeedbackResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/feedback"


def test_feedback_success_examples_match_ledger_and_openapi() -> None:
    expected = build_feedback_response_examples()
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == OPERATION_PATH
    )
    ledger_examples = [json.loads(value) for value in endpoint["response_examples"]]
    operation = app.openapi()["paths"][OPERATION_PATH]["post"]
    openapi_examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    published = {name: metadata["value"] for name, metadata in openapi_examples.items()}

    assert ledger_examples == list(expected.values())
    assert published == expected
    assert all(FeedbackResponse.model_validate(value) for value in expected.values())

    assert expected["accepted"]["feedbackEvent"] is not None
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["feedbackEvent"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())
