from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_review_identity_contract_gate_accepts_repository_contract() -> None:
    module = _load_gate()

    assert module.validate_review_identity_contract() == []


def test_review_identity_contract_gate_rejects_non_atomic_postgres_identity_claim(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.REQUIRED_FRAGMENTS:
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    snapshot_writes_path = tmp_path / "src/app/infrastructure/postgres_snapshot_writes.py"
    snapshot_writes_path.write_text(
        snapshot_writes_path.read_text(encoding="utf-8").replace(
            "ON CONFLICT (review_decision_id) DO NOTHING",
            "removed review identity conflict handling",
        ),
        encoding="utf-8",
    )

    errors = module.validate_review_identity_contract(tmp_path)

    assert any("ON CONFLICT (review_decision_id) DO NOTHING" in error for error in errors)


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/review_identity_contract_gate.py"
    spec = importlib.util.spec_from_file_location("review_identity_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
