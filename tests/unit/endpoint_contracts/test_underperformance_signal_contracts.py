from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from app.api.examples.underperformance_signal import (
    build_source_backed_underperformance_evaluation_response_examples,
    build_underperformance_evaluation_response_examples,
)
from app.main import app


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_underperformance_signal_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_underperformance_signal_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_underperformance_evaluation_contract_blocks_openapi_drift() -> None:
    module = _load_contract_module()
    expected = build_underperformance_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.UNDERPERFORMANCE_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.UNDERPERFORMANCE_CALLER_CANDIDATE_TEST,
            module.UNDERPERFORMANCE_CALLER_BLOCKED_TEST,
            module.UNDERPERFORMANCE_CALLER_SUPPRESSED_TEST,
            module.UNDERPERFORMANCE_CALLER_NOT_ELIGIBLE_TEST,
            module.UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("suppressed")

    errors = module.validate_underperformance_evaluation_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/underperformance/evaluate'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "underperformance-evaluation success mode"
        )
    ]


def test_source_backed_underperformance_contract_blocks_ledger_drift() -> None:
    module = _load_contract_module()
    expected = build_source_backed_underperformance_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION[1],
        "response_examples": [json.dumps(expected["candidateCreated"])],
        "test_evidence": [
            module.UNDERPERFORMANCE_SOURCE_CANDIDATE_TEST,
            module.UNDERPERFORMANCE_SOURCE_BLOCKED_TEST,
            module.UNDERPERFORMANCE_SOURCE_NON_CANDIDATE_TEST,
            module.UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_source_backed_underperformance_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/underperformance/evaluate-from-source'): "
            "response_examples must exactly match every code-owned "
            "source-backed-underperformance-evaluation success mode"
        )
    ]


def test_underperformance_contract_blocks_missing_behavior_evidence() -> None:
    module = _load_contract_module()
    expected = build_underperformance_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.UNDERPERFORMANCE_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.UNDERPERFORMANCE_CALLER_CANDIDATE_TEST,
            module.UNDERPERFORMANCE_CALLER_BLOCKED_TEST,
            module.UNDERPERFORMANCE_CALLER_NOT_ELIGIBLE_TEST,
            module.UNDERPERFORMANCE_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_underperformance_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/underperformance/evaluate'): "
            "test_evidence must cite the suppressed HTTP behavior test"
        )
    ]
