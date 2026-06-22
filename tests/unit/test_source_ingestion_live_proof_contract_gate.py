from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "source_ingestion_live_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "source_ingestion_live_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_ingestion_live_proof_contract_gate_passes() -> None:
    module = _load_gate()

    assert module.validate_source_ingestion_live_proof_contract() == []


def test_source_ingestion_live_proof_contract_gate_blocks_sensitive_fields() -> None:
    module = _load_gate()
    errors: list[str] = []

    module._validate_forbidden_content(
        {
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "idempotencyKey": "signal-ingestion:high-cash:lotus-core:raw",
            "candidateId": "idea_high_cash_candidate",
        },
        errors,
    )

    assert "$.portfolioId: forbidden source-sensitive key is present" in errors
    assert "$.idempotencyKey: forbidden source-sensitive key is present" in errors
    assert "$.candidateId: forbidden source-sensitive key is present" in errors
    assert (
        "$.portfolioId: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present" in errors
    )
    assert (
        "$.idempotencyKey: forbidden source-sensitive text "
        "`signal-ingestion:high-cash:lotus-core` is present"
    ) in errors
