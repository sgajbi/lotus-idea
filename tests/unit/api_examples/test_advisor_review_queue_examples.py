from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

from app.api.examples.advisor_review_queue import (
    ADVISOR_REVIEW_QUEUE_OPERATION_PATH,
    build_advisor_review_queue_response_examples,
)
from app.api.review_queue_models import BusinessReviewQueueResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def test_advisor_review_queue_examples_execute_real_projection_and_preserve_boundary() -> None:
    examples = build_advisor_review_queue_response_examples()

    assert tuple(examples) == ("itemsAvailable", "noItemsAvailable")
    assert all(BusinessReviewQueueResponse.model_validate(example) for example in examples.values())
    assert examples["itemsAvailable"]["audience"] == "advisor"
    assert examples["itemsAvailable"]["items"][0]["candidate"]["reviewPosture"] == (
        "advisor_review_required"
    )
    assert examples["itemsAvailable"]["page"]["totalReviewableItemCount"] == 1
    assert examples["noItemsAvailable"]["items"] == []
    assert examples["noItemsAvailable"]["page"]["totalReviewableItemCount"] == 0
    assert all(example["durableStorageBacked"] is False for example in examples.values())
    assert all(example["supportedFeaturePromoted"] is False for example in examples.values())


def test_advisor_review_queue_examples_match_ledger_and_generated_openapi() -> None:
    expected = build_advisor_review_queue_response_examples()

    assert _ledger_examples() == list(expected.values())
    assert _openapi_examples() == expected


def test_advisor_review_queue_contract_blocks_missing_openapi_success_mode() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint()
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][ADVISOR_REVIEW_QUEUE_OPERATION_PATH]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["examples"]
    examples.pop("noItemsAvailable")

    errors = module.validate_advisor_review_queue_success_contract(endpoint, openapi_spec)

    assert errors == [
        "('GET', '/api/v1/review-queues/advisor'): OpenAPI 200 examples must exactly match "
        "every named code-owned advisor-review-queue success mode"
    ]


def test_advisor_review_queue_contract_blocks_missing_empty_queue_behavior_evidence() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint()
    endpoint["test_evidence"].remove(
        "tests/integration/test_review_queue_api.py::"
        "test_advisor_review_queue_api_returns_empty_queue_without_candidates"
    )

    errors = module.validate_advisor_review_queue_success_contract(endpoint)

    assert any("empty-queue HTTP behavior test" in error for error in errors)


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_advisor_review_queue_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_advisor_review_queue_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger_endpoint() -> dict[str, Any]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return deepcopy(
        next(
            endpoint
            for endpoint in ledger["endpoints"]
            if endpoint["method"] == "GET"
            and endpoint["path"] == ADVISOR_REVIEW_QUEUE_OPERATION_PATH
        )
    )


def _ledger_examples() -> list[dict[str, object]]:
    return [json.loads(value) for value in _ledger_endpoint()["response_examples"]]


def _openapi_examples() -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][ADVISOR_REVIEW_QUEUE_OPERATION_PATH]["get"]
    examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
