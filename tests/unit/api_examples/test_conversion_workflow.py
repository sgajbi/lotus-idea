from __future__ import annotations

import json
from pathlib import Path

from app.api.conversion_governance_models import (
    ConversionIntentApiResponse,
    ConversionOutcomeApiResponse,
)
from app.api.examples.conversion_workflow import (
    build_conversion_intent_response_examples,
    build_conversion_outcome_response_examples,
)
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
CONVERSION_INTENT_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/conversion-intents"
CONVERSION_OUTCOME_OPERATION_PATH = "/api/v1/conversion-intents/{conversionIntentId}/outcomes"


def test_conversion_intent_success_examples_match_ledger_and_openapi() -> None:
    expected = build_conversion_intent_response_examples()

    assert _ledger_examples(CONVERSION_INTENT_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(CONVERSION_INTENT_OPERATION_PATH) == expected
    assert all(ConversionIntentApiResponse.model_validate(value) for value in expected.values())

    intent = expected["accepted"]["conversionIntent"]
    assert intent is not None
    assert intent["grantsDownstreamAuthority"] is False
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["conversionIntent"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())


def test_conversion_outcome_success_examples_match_ledger_and_openapi() -> None:
    expected = build_conversion_outcome_response_examples()

    assert _ledger_examples(CONVERSION_OUTCOME_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(CONVERSION_OUTCOME_OPERATION_PATH) == expected
    assert all(ConversionOutcomeApiResponse.model_validate(value) for value in expected.values())

    outcome = expected["accepted"]["conversionOutcome"]
    assert outcome is not None
    assert outcome["supersedesConversionOutcomeId"] is None
    assert outcome["correctionReason"] is None
    assert outcome["grantsExecutionAuthority"] is False
    assert outcome["grantsClientCommunicationAuthority"] is False
    assert outcome["grantsSuitabilityAuthority"] is False
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["conversionOutcome"] is None
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
