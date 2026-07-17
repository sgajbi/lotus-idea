from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from app.api.examples.allocation_drift_signal import (
    build_allocation_drift_evaluation_response_examples,
    build_source_backed_allocation_drift_evaluation_response_examples,
)
from app.main import app


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_allocation_drift_signal_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_allocation_drift_signal_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_allocation_drift_evaluation_contract_blocks_openapi_drift() -> None:
    module = _load_contract_module()
    expected = build_allocation_drift_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.ALLOCATION_DRIFT_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.ALLOCATION_DRIFT_CALLER_CANDIDATE_TEST,
            module.ALLOCATION_DRIFT_CALLER_BLOCKED_TEST,
            module.ALLOCATION_DRIFT_CALLER_SUPPRESSED_TEST,
            module.ALLOCATION_DRIFT_CALLER_NOT_ELIGIBLE_TEST,
            module.ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("suppressed")

    errors = module.validate_allocation_drift_evaluation_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/allocation-drift/evaluate'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "allocation-drift-evaluation success mode"
        )
    ]


def test_source_backed_allocation_drift_contract_blocks_ledger_drift() -> None:
    module = _load_contract_module()
    expected = build_source_backed_allocation_drift_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION[1],
        "response_examples": [json.dumps(expected["candidateCreated"])],
        "test_evidence": [
            module.ALLOCATION_DRIFT_SOURCE_CANDIDATE_TEST,
            module.ALLOCATION_DRIFT_SOURCE_BLOCKED_TEST,
            module.ALLOCATION_DRIFT_SOURCE_NON_CANDIDATE_TEST,
            module.ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_source_backed_allocation_drift_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/allocation-drift/evaluate-from-source'): "
            "response_examples must exactly match every code-owned "
            "source-backed-allocation-drift-evaluation success mode"
        )
    ]


def test_allocation_drift_contract_blocks_missing_behavior_evidence() -> None:
    module = _load_contract_module()
    expected = build_allocation_drift_evaluation_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.ALLOCATION_DRIFT_EVALUATE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.ALLOCATION_DRIFT_CALLER_CANDIDATE_TEST,
            module.ALLOCATION_DRIFT_CALLER_BLOCKED_TEST,
            module.ALLOCATION_DRIFT_CALLER_NOT_ELIGIBLE_TEST,
            module.ALLOCATION_DRIFT_SUCCESS_CONTRACT_TEST,
        ],
    }

    errors = module.validate_allocation_drift_evaluation_success_contract(endpoint)

    assert errors == [
        (
            "('POST', '/api/v1/idea-signals/allocation-drift/evaluate'): "
            "test_evidence must cite the suppressed HTTP behavior test"
        )
    ]
