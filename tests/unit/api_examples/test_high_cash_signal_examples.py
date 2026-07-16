from __future__ import annotations

import json
from pathlib import Path

from app.api.examples.high_cash_signal import (
    HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION_PATH,
    HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION_PATH,
    HIGH_CASH_EVALUATE_OPERATION_PATH,
    build_high_cash_evaluation_response_examples,
    build_high_cash_persistence_response_examples,
    build_source_backed_high_cash_evaluation_response_examples,
)
from app.api.idea_signal_models import (
    EvaluateAndPersistHighCashSignalResponse,
    EvaluateHighCashSignalResponse,
)
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")


def test_high_cash_evaluation_examples_cover_every_domain_outcome() -> None:
    caller_examples = build_high_cash_evaluation_response_examples()
    source_examples = build_source_backed_high_cash_evaluation_response_examples()

    assert tuple(caller_examples) == (
        "candidateCreated",
        "blocked",
        "suppressed",
        "notEligible",
    )
    assert tuple(source_examples) == tuple(caller_examples)
    assert _outcomes(caller_examples) == {
        "candidate_created",
        "blocked",
        "suppressed",
        "not_eligible",
    }
    assert _outcomes(source_examples) == _outcomes(caller_examples)
    assert all(
        EvaluateHighCashSignalResponse.model_validate(example)
        for example in (*caller_examples.values(), *source_examples.values())
    )
    assert caller_examples["candidateCreated"]["candidate"] is not None
    assert source_examples["candidateCreated"]["candidate"]["sourceRefs"]
    assert caller_examples["blocked"]["unsupportedReasons"] == ["stale_source"]
    assert caller_examples["suppressed"]["candidate"] is None
    assert caller_examples["notEligible"]["candidate"] is None
    assert all(
        example["supportedFeaturePromoted"] is False
        for example in (*caller_examples.values(), *source_examples.values())
    )


def test_high_cash_persistence_examples_cover_retry_and_no_write_modes() -> None:
    examples = build_high_cash_persistence_response_examples()

    assert tuple(examples) == (
        "accepted",
        "replayed",
        "duplicateCandidate",
        "blocked",
        "suppressed",
        "notEligible",
    )
    assert all(
        EvaluateAndPersistHighCashSignalResponse.model_validate(example)
        for example in examples.values()
    )
    assert {
        name: example["persistence"]["decision"] if example["persistence"] else None
        for name, example in examples.items()
    } == {
        "accepted": "accepted",
        "replayed": "replayed",
        "duplicateCandidate": "duplicate_candidate",
        "blocked": None,
        "suppressed": None,
        "notEligible": None,
    }
    assert (
        examples["accepted"]["persistence"]["candidateId"]
        == examples["replayed"]["persistence"]["candidateId"]
    )
    assert (
        examples["accepted"]["persistence"]["candidateId"]
        == examples["duplicateCandidate"]["persistence"]["candidateId"]
    )
    assert examples["blocked"]["evaluation"]["outcome"] == "blocked"
    assert examples["suppressed"]["evaluation"]["outcome"] == "suppressed"
    assert examples["notEligible"]["evaluation"]["outcome"] == "not_eligible"
    assert all(example["durableStorageBacked"] is False for example in examples.values())
    assert all(example["supportedFeaturePromoted"] is False for example in examples.values())


def test_high_cash_examples_match_ledger_and_generated_openapi() -> None:
    expected_by_path = {
        HIGH_CASH_EVALUATE_OPERATION_PATH: build_high_cash_evaluation_response_examples(),
        HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION_PATH: (
            build_source_backed_high_cash_evaluation_response_examples()
        ),
        HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION_PATH: (
            build_high_cash_persistence_response_examples()
        ),
    }

    for operation_path, expected in expected_by_path.items():
        assert _ledger_examples(operation_path) == list(expected.values())
        assert _openapi_examples(operation_path) == expected


def _outcomes(examples: dict[str, dict[str, object]]) -> set[object]:
    return {example["outcome"] for example in examples.values()}


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
