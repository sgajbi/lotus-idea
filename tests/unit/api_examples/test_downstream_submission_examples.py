from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

from app.api.examples.downstream_submission import (
    CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
    REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
    _ExampleDownstreamSubmissionRepository,
    build_conversion_downstream_submission_200_response_examples,
    build_conversion_downstream_submission_202_response_examples,
    build_report_downstream_submission_200_response_examples,
    build_report_downstream_submission_202_response_examples,
)
from app.api.downstream_realization import DownstreamSubmissionApiResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def test_downstream_submission_examples_preserve_authority_and_replay_safety() -> None:
    examples = (
        build_conversion_downstream_submission_200_response_examples(),
        build_conversion_downstream_submission_202_response_examples(),
        build_report_downstream_submission_200_response_examples(),
        build_report_downstream_submission_202_response_examples(),
    )
    assert all(
        DownstreamSubmissionApiResponse.model_validate(payload)
        for group in examples
        for payload in group.values()
    )
    for success_examples in (
        examples[0],
        examples[2],
    ):
        assert tuple(success_examples) == (
            "accepted",
            "rejected",
            "acceptedReplayed",
            "rejectedReplayed",
        )
        assert success_examples["accepted"]["downstreamSubmission"]["idempotencyReplayed"] is False
        assert (
            success_examples["acceptedReplayed"]["downstreamSubmission"]["idempotencyReplayed"]
            is True
        )
        assert success_examples["rejected"]["downstreamSubmission"]["idempotencyReplayed"] is False
        assert (
            success_examples["rejectedReplayed"]["downstreamSubmission"]["idempotencyReplayed"]
            is True
        )
    for reconciliation_examples in (examples[1], examples[3]):
        submission = reconciliation_examples["reconciliationRequired"]["downstreamSubmission"]
        assert submission["submissionStatus"] == "reconciliation_required"
        assert submission["idempotencyReplayed"] is False
    for group in examples:
        for payload in group.values():
            submission = payload["downstreamSubmission"]
            assert submission["recordsDownstreamOutcome"] is False
            assert submission["grantsDownstreamAuthority"] is False
            assert submission["supportedFeaturePromoted"] is False
            assert payload["durableStorageBacked"] is False
            assert payload["supportedFeaturePromoted"] is False


def test_downstream_submission_example_repository_does_not_return_scope_for_another_pack() -> None:
    repository = _ExampleDownstreamSubmissionRepository()

    assert repository.candidate_record_for_report_evidence_pack("another-report-pack") is None


def test_downstream_submission_examples_match_ledger_and_generated_openapi() -> None:
    expected_by_path = {
        CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH: (
            build_conversion_downstream_submission_200_response_examples(),
            build_conversion_downstream_submission_202_response_examples(),
        ),
        REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH: (
            build_report_downstream_submission_200_response_examples(),
            build_report_downstream_submission_202_response_examples(),
        ),
    }
    for operation_path, (expected_200, expected_202) in expected_by_path.items():
        assert _ledger_examples(operation_path) == [*expected_200.values(), *expected_202.values()]
        assert _openapi_examples(operation_path, "200") == expected_200
        assert _openapi_examples(operation_path, "202") == expected_202


def test_downstream_submission_contract_blocks_missing_202_success_mode() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint(CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH)
    openapi_spec = deepcopy(app.openapi())
    openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["examples"].clear()
    assert module.validate_conversion_downstream_submission_success_contract(
        endpoint, openapi_spec
    ) == [
        "('POST', '/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions'): "
        "OpenAPI 202 examples must exactly match every named code-owned "
        "conversion-downstream-submission success mode"
    ]


def test_downstream_submission_contract_blocks_missing_202_behavior_evidence() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint(REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH)
    endpoint["test_evidence"].remove(
        "tests/integration/test_downstream_realization_api.py::"
        "test_report_downstream_submission_api_returns_durable_uncertain_posture"
    )
    errors = module.validate_report_downstream_submission_success_contract(endpoint)
    assert any("202 reconciliation-required behavior test" in error for error in errors)


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_downstream_submission_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_downstream_submission_contracts", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger_endpoint(path: str) -> dict[str, Any]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return deepcopy(next(endpoint for endpoint in ledger["endpoints"] if endpoint["path"] == path))


def _ledger_examples(operation_path: str) -> list[dict[str, object]]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == operation_path
    )
    return [json.loads(value) for value in endpoint["response_examples"]]


def _openapi_examples(operation_path: str, status_code: str) -> dict[str, dict[str, object]]:
    examples = app.openapi()["paths"][operation_path]["post"]["responses"][status_code]["content"][
        "application/json"
    ]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
