from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    path = ROOT / "scripts" / "service_resource_baseline_contract_gate.py"
    spec = importlib.util.spec_from_file_location("service_resource_baseline_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resource_baseline_contract_passes_current_foundation() -> None:
    assert _load_gate().validate_contract() == []


def test_resource_baseline_contract_rejects_claim_inflation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_gate()

    def inflated(**kwargs: object) -> dict[str, object]:
        return {
            "certificationBlockers": [],
            "costAttributionVerified": True,
            "certificationReady": True,
        }

    monkeypatch.setattr(module, "build_service_resource_baseline", inflated)
    monkeypatch.setattr(module, "validate_service_resource_baseline", lambda artifact: [])

    errors = module.validate_contract()

    assert "resource baseline must preserve production-like and cost blockers" in errors
    assert "resource baseline must not infer cost evidence from process metrics" in errors
    assert "controlled resource baseline must remain non-certifying" in errors
