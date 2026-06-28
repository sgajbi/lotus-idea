from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _makefile_without(lint_call: str, script: str | None = None) -> str:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8").replace(lint_call, "")
    if script:
        makefile = makefile.replace(script, "scripts/removed.py")
    return makefile


def test_ci_contract_gate_blocks_missing_ai_model_risk_operations_proof_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without(
            "$(MAKE) ai-model-risk-operations-proof-contract-gate\n",
            "scripts/ai_model_risk_operations_proof_contract_gate.py",
        )
    )

    assert (
        "Makefile lint target must call `$(MAKE) ai-model-risk-operations-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile ai-model-risk-operations-proof-contract-gate target must run "
        "`scripts/ai_model_risk_operations_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_high_volatility_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without(
            "$(MAKE) high-volatility-live-proof-contract-gate\n",
            "scripts/high_volatility_live_proof_contract_gate.py",
        )
    )

    assert (
        "Makefile lint target must call `$(MAKE) high-volatility-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile high-volatility-live-proof-contract-gate target must run "
        "`scripts/high_volatility_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_risk_drawdown_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without(
            "$(MAKE) risk-drawdown-live-proof-contract-gate\n",
            "scripts/risk_drawdown_live_proof_contract_gate.py",
        )
    )

    assert (
        "Makefile lint target must call `$(MAKE) risk-drawdown-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile risk-drawdown-live-proof-contract-gate target must run "
        "`scripts/risk_drawdown_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_mandate_restriction_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without(
            "$(MAKE) mandate-restriction-live-proof-contract-gate\n",
            "scripts/mandate_restriction_live_proof_contract_gate.py",
        )
    )

    assert (
        "Makefile lint target must call `$(MAKE) mandate-restriction-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile mandate-restriction-live-proof-contract-gate target must run "
        "`scripts/mandate_restriction_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_implementation_proof_readiness_lint_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without("$(MAKE) implementation-proof-readiness-check\n")
    )

    assert (
        "Makefile lint target must call `$(MAKE) implementation-proof-readiness-check`"
    ) in errors


def test_ci_contract_gate_blocks_missing_runtime_trust_telemetry_preview_gate() -> None:
    module = _load_ci_contract_gate()
    errors = module.validate_makefile(
        _makefile_without(
            "$(MAKE) runtime-trust-telemetry-preview-check\n",
            "scripts/generate_runtime_trust_telemetry_preview.py",
        )
    )

    assert (
        "Makefile lint target must call `$(MAKE) runtime-trust-telemetry-preview-check`"
    ) in errors
    assert (
        "Makefile runtime-trust-telemetry-preview-check target must run "
        "`scripts/generate_runtime_trust_telemetry_preview.py`"
    ) in errors
