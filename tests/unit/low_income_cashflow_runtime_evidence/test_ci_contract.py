from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_blocks_missing_low_income_cashflow_runtime_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF",
            "REMOVED_LOW_INCOME_CORE_CASHFLOW_PROOF",
        )
        .replace(
            "--low-income-core-cashflow-live-proof",
            "--removed-low-income-core-cashflow-live-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support optional "
        "Core cashflow live proof artifact wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must pass optional Core "
        "cashflow live proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_low_income_cashflow_runtime_gate() -> None:
    module = _load_ci_contract_gate()
    script = "scripts/low_income_cashflow_runtime_evidence/runtime_execution_contract_gate.py"
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) low-income-core-cashflow-live-proof-contract-gate\n", "")
        .replace(script, "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) low-income-core-cashflow-live-proof-contract-gate`"
    ) in errors
    assert (
        f"Makefile low-income-core-cashflow-live-proof-contract-gate target must run `{script}`"
    ) in errors
