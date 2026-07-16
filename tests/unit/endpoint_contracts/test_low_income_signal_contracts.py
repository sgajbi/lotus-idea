from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from app.api.examples.low_income_signal import (
    build_low_income_evaluation_response_examples,
    build_source_backed_low_income_evaluation_response_examples,
)
from app.main import app


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_low_income_signal_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_low_income_signal_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_low_income_evaluation_contract_blocks_openapi_drift() -> None:
    module = _load_contract_module()
    expected = build_low_income_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.LOW_INCOME_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.LOW_INCOME_CALLER_CANDIDATE_TEST,
            module.LOW_INCOME_CALLER_BLOCKED_TEST,
            module.LOW_INCOME_CALLER_SUPPRESSED_TEST,
            module.LOW_INCOME_CALLER_NOT_ELIGIBLE_TEST,
            module.LOW_INCOME_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("suppressed")

    errors = module.validate_low_income_evaluation_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/low-income/evaluate'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "low-income-evaluation success mode"
        )
    ]


def test_source_backed_low_income_contract_blocks_ledger_drift() -> None:
    module = _load_contract_module()
    expected = build_source_backed_low_income_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION[1],
        "response_examples": [json.dumps(expected["candidateCreated"])],
        "test_evidence": [
            module.LOW_INCOME_SOURCE_CANDIDATE_TEST,
            module.LOW_INCOME_SOURCE_BLOCKED_TEST,
            module.LOW_INCOME_SOURCE_NON_CANDIDATE_TEST,
            module.LOW_INCOME_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_source_backed_low_income_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/low-income/evaluate-from-source'): "
            "response_examples must exactly match every code-owned "
            "source-backed-low-income-evaluation success mode"
        )
    ]


def test_low_income_contract_blocks_missing_behavior_evidence() -> None:
    module = _load_contract_module()
    expected = build_low_income_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.LOW_INCOME_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.LOW_INCOME_CALLER_CANDIDATE_TEST,
            module.LOW_INCOME_CALLER_BLOCKED_TEST,
            module.LOW_INCOME_CALLER_NOT_ELIGIBLE_TEST,
            module.LOW_INCOME_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_low_income_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/low-income/evaluate'): "
            "test_evidence must cite the suppressed HTTP behavior test"
        )
    ]
