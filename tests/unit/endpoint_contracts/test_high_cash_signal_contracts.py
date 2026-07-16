from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from app.api.examples.high_cash_signal import (
    build_high_cash_evaluation_response_examples,
    build_high_cash_persistence_response_examples,
    build_source_backed_high_cash_evaluation_response_examples,
)
from app.main import app


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_high_cash_signal_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_high_cash_signal_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_high_cash_evaluation_contract_blocks_openapi_drift() -> None:
    module = _load_contract_module()
    expected = build_high_cash_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.HIGH_CASH_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.HIGH_CASH_CALLER_CANDIDATE_TEST,
            module.HIGH_CASH_CALLER_BLOCKED_TEST,
            module.HIGH_CASH_CALLER_NON_CANDIDATE_TEST,
            module.HIGH_CASH_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("suppressed")

    errors = module.validate_high_cash_evaluation_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/high-cash/evaluate'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "high-cash-evaluation success mode"
        )
    ]


def test_source_backed_high_cash_contract_blocks_ledger_drift() -> None:
    module = _load_contract_module()
    expected = build_source_backed_high_cash_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION[1],
        "response_examples": [json.dumps(expected["candidateCreated"])],
        "test_evidence": [
            module.HIGH_CASH_SOURCE_CANDIDATE_TEST,
            module.HIGH_CASH_SOURCE_BLOCKED_TEST,
            module.HIGH_CASH_SOURCE_NON_CANDIDATE_TEST,
            module.HIGH_CASH_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_source_backed_high_cash_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/high-cash/evaluate-from-source'): "
            "response_examples must exactly match every code-owned "
            "source-backed-high-cash-evaluation success mode"
        )
    ]


def test_high_cash_persistence_contract_blocks_missing_behavior_evidence() -> None:
    module = _load_contract_module()
    expected = build_high_cash_persistence_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.HIGH_CASH_PERSIST_ACCEPTED_TEST,
            module.HIGH_CASH_PERSIST_REPLAYED_TEST,
            module.HIGH_CASH_PERSIST_BLOCKED_TEST,
            module.HIGH_CASH_PERSIST_NON_CANDIDATE_TEST,
            module.HIGH_CASH_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_high_cash_persistence_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/high-cash/evaluate-and-persist'): "
            "test_evidence must cite the duplicate-candidate behavior test"
        )
    ]
