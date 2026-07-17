from __future__ import annotations

import json
from pathlib import Path

from app.api.examples.underperformance_signal import (
    UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION_PATH,
    UNDERPERFORMANCE_EVALUATE_OPERATION_PATH,
    build_source_backed_underperformance_evaluation_response_examples,
    build_underperformance_evaluation_response_examples,
)
from app.api.underperformance_signals import EvaluateUnderperformanceSignalResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")


def test_underperformance_examples_cover_every_domain_outcome_and_authority_boundary() -> None:
    caller_examples = build_underperformance_evaluation_response_examples()
    source_examples = build_source_backed_underperformance_evaluation_response_examples()

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
        EvaluateUnderperformanceSignalResponse.model_validate(example)
        for example in (*caller_examples.values(), *source_examples.values())
    )

    for examples in (caller_examples, source_examples):
        candidate = examples["candidateCreated"]["candidate"]
        assert candidate is not None
        assert candidate["reviewPosture"] == "advisor_review_required"
        assert {ref["productId"] for ref in candidate["sourceRefs"]} == {
            "lotus-performance:ReturnsSeriesBundle:v1"
        }
        assert all(
            "route" not in ref and "contentHash" not in ref for ref in candidate["sourceRefs"]
        )
        assert examples["suppressed"]["candidate"] is None
        assert examples["notEligible"]["candidate"] is None
        assert all(
            example["sourceAuthority"] == "lotus-performance" for example in examples.values()
        )
        assert all(example["supportedFeaturePromoted"] is False for example in examples.values())

    assert caller_examples["blocked"]["unsupportedReasons"] == ["stale_source"]
    assert source_examples["blocked"]["unsupportedReasons"] == ["source_unavailable"]


def test_underperformance_examples_match_ledger_and_generated_openapi() -> None:
    expected_by_path = {
        UNDERPERFORMANCE_EVALUATE_OPERATION_PATH: (
            build_underperformance_evaluation_response_examples()
        ),
        UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION_PATH: (
            build_source_backed_underperformance_evaluation_response_examples()
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
