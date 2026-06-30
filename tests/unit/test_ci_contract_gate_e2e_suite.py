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


def test_ci_contract_gate_blocks_missing_critical_e2e_workflow(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    e2e_dir = tmp_path / "tests" / "e2e"
    e2e_dir.mkdir(parents=True)

    errors = module.validate_e2e_suite(e2e_dir)

    assert (
        "tests/e2e missing required critical workflow proof `test_critical_idea_workflow.py`"
        in errors
    )


def test_ci_contract_gate_blocks_weakened_critical_e2e_workflow(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    e2e_dir = tmp_path / "tests" / "e2e"
    e2e_dir.mkdir(parents=True)
    source = ROOT / "tests" / "e2e" / "test_critical_idea_workflow.py"
    weakened = source.read_text(encoding="utf-8").replace(
        '"grantsClientPublicationAuthority"', '"publicationBoundaryNotAsserted"'
    )
    (e2e_dir / "test_critical_idea_workflow.py").write_text(weakened, encoding="utf-8")

    errors = module.validate_e2e_suite(e2e_dir)

    assert (
        "tests/e2e/test_critical_idea_workflow.py missing critical workflow assertion "
        '`"grantsClientPublicationAuthority"`'
    ) in errors
