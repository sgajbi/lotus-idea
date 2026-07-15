from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[3]


def _load_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "source_ingestion" / "runtime_execution_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "source_ingestion_runtime_execution_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_ingestion_runtime_execution_contract_gate_passes() -> None:
    module = _load_contract_gate()

    assert module.validate_source_ingestion_runtime_execution_contract() == []


def test_source_ingestion_runtime_execution_contract_gate_blocks_sensitive_fields() -> None:
    module = _load_contract_gate()
    errors: list[str] = []

    module._validate_forbidden_content(
        {
            "tenantId": "tenant-a",
            "nested": {"sourceRoute": "/api/v1/private"},
        },
        errors,
        "payload",
    )

    assert errors
