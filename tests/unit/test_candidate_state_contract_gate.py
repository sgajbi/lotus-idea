from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_candidate_state_contract_gate_accepts_repository_contract() -> None:
    module = _load_gate()

    assert module.validate_candidate_state_contract() == []


def test_candidate_state_contract_gate_rejects_removed_domain_validation(tmp_path: Path) -> None:
    module = _load_gate()
    for relative_path in module.REQUIRED_FRAGMENTS:
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    ideas_path = tmp_path / "src/app/domain/ideas.py"
    ideas_path.write_text(
        ideas_path.read_text(encoding="utf-8").replace(
            "validate_candidate_state(",
            "removed_candidate_state_validation(",
        ),
        encoding="utf-8",
    )

    errors = module.validate_candidate_state_contract(tmp_path)

    assert any("missing required fragment `validate_candidate_state(`" in error for error in errors)


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/candidate_state_contract_gate.py"
    spec = importlib.util.spec_from_file_location("candidate_state_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
