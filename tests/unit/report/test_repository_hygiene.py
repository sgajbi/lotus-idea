from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[3]


def _load_repository_hygiene_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "repository_hygiene_gate.py"
    spec = importlib.util.spec_from_file_location("repository_hygiene_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_hygiene_gate_enforces_report_materialization_proof_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/report/generate_materialization_runtime_execution.py",
        "scripts/report/generate_materialization_source_contract.py",
        "scripts/report/materialization_runtime_execution_gate.py",
        "scripts/report/materialization_source_contract_gate.py",
        "src/app/application/report/materialization_runtime_execution.py",
        "src/app/application/report/materialization_source_contract.py",
        "tests/unit/report/test_materialization_runtime_execution.py",
        "tests/unit/report/test_materialization_source_contract.py",
    }
    retired_paths = {
        "scripts/generate_report_materialization_proof.py",
        "scripts/report_materialization_proof_contract_gate.py",
        "src/app/application/report_materialization_proof.py",
        "tests/unit/test_report_materialization_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )
