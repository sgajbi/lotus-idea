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


def test_ci_contract_gate_blocks_coverage_gate_target_drift() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(VENV_PYTHON) scripts/coverage_gate.py --coverage-dir $(COVERAGE_DATA_DIR)",
            "$(VENV_PYTHON) -m coverage report --fail-under=99",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile coverage-gate target must run "
        "`$(VENV_PYTHON) scripts/coverage_gate.py --coverage-dir $(COVERAGE_DATA_DIR)`"
    ) in errors
