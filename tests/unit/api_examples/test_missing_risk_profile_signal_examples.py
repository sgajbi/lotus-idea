from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

from app.api.examples.missing_risk_profile_signal import (
    MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH,
    MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH,
    build_missing_risk_profile_evaluation_response_examples,
    build_source_backed_missing_risk_profile_evaluation_response_examples,
)
from app.api.missing_risk_profile_signals import EvaluateMissingRiskProfileSignalResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def test_missing_risk_profile_examples_cover_every_domain_outcome_and_authority() -> None:
    caller_examples = build_missing_risk_profile_evaluation_response_examples()
    source_examples = build_source_backed_missing_risk_profile_evaluation_response_examples()

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
        EvaluateMissingRiskProfileSignalResponse.model_validate(example)
        for example in (*caller_examples.values(), *source_examples.values())
    )

    for examples in (caller_examples, source_examples):
        candidate = examples["candidateCreated"]["candidate"]
        assert candidate is not None
        assert candidate["reviewPosture"] == "advisor_review_required"
        assert {ref["productId"] for ref in candidate["sourceRefs"]} == {
            "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
        }
        assert all(
            "route" not in ref and "contentHash" not in ref for ref in candidate["sourceRefs"]
        )
        assert examples["suppressed"]["candidate"] is None
        assert examples["notEligible"]["candidate"] is None
        assert all(example["sourceAuthority"] == "lotus-advise" for example in examples.values())
        assert all(example["supportedFeaturePromoted"] is False for example in examples.values())

    assert caller_examples["blocked"]["unsupportedReasons"] == ["stale_source"]
    assert source_examples["blocked"]["unsupportedReasons"] == ["source_unavailable"]


def test_missing_risk_profile_examples_match_ledger_and_generated_openapi() -> None:
    expected_by_path = {
        MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH: (
            build_missing_risk_profile_evaluation_response_examples()
        ),
        MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH: (
            build_source_backed_missing_risk_profile_evaluation_response_examples()
        ),
    }

    for operation_path, expected in expected_by_path.items():
        assert _ledger_examples(operation_path) == list(expected.values())
        assert _openapi_examples(operation_path) == expected


def test_missing_risk_profile_contract_blocks_missing_openapi_success_mode() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint(MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH)
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("suppressed")

    errors = module.validate_missing_risk_profile_evaluation_success_contract(
        endpoint,
        openapi_spec,
    )

    assert errors == [
        "('POST', '/api/v1/idea-signals/missing-risk-profile/evaluate'): OpenAPI 200 "
        "examples must exactly match every named code-owned missing-risk-profile-evaluation "
        "success mode"
    ]


def test_missing_risk_profile_contract_blocks_missing_behavior_evidence() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint(MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH)
    endpoint["test_evidence"].remove(
        "tests/integration/test_missing_risk_profile_signal_api.py::"
        "test_missing_risk_profile_signal_from_source_exposes_non_candidate_success_modes"
    )

    errors = module.validate_source_backed_missing_risk_profile_evaluation_success_contract(
        endpoint
    )

    assert any(
        "source-backed suppressed and not-eligible behavior test" in error for error in errors
    )


def _outcomes(examples: dict[str, dict[str, object]]) -> set[object]:
    return {example["outcome"] for example in examples.values()}


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_missing_risk_profile_signal_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_missing_risk_profile_signal_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
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


def _openapi_examples(operation_path: str) -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][operation_path]["post"]
    examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
