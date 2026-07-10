from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_conversion_outcome_contract_gate_accepts_repository_contract() -> None:
    module = _load_gate()

    assert module.validate_conversion_outcome_contract() == []


def test_conversion_outcome_contract_gate_rejects_non_atomic_postgres_claim(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.REQUIRED_FRAGMENTS:
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    adapter_path = tmp_path / "src/app/infrastructure/postgres_conversion_outcome.py"
    adapter_path.write_text(
        adapter_path.read_text(encoding="utf-8").replace(
            "ON CONFLICT DO NOTHING",
            "removed conversion outcome conflict handling",
        ),
        encoding="utf-8",
    )

    errors = module.validate_conversion_outcome_contract(tmp_path)

    assert any("ON CONFLICT DO NOTHING" in error for error in errors)


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/conversion_outcome_contract_gate.py"
    spec = importlib.util.spec_from_file_location("conversion_outcome_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
