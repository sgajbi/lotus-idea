from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_outbox_recovery_contract_gate_accepts_repository_contract() -> None:
    module = _load_gate()

    assert module.validate_outbox_recovery_contract() == []


def test_outbox_recovery_contract_gate_rejects_sensitive_response_field(tmp_path: Path) -> None:
    module = _load_gate()
    for relative_path in module.REQUIRED_FRAGMENTS:
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    events_target = tmp_path / "src/app/domain/events.py"
    events_target.parent.mkdir(parents=True, exist_ok=True)
    events_target.write_text(
        (ROOT / "src/app/domain/events.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    response_target = tmp_path / "src/app/api/outbox_recovery_models.py"
    response_target.parent.mkdir(parents=True, exist_ok=True)
    response_target.write_text("class UnsafeResponse:\n    payload: dict\n", encoding="utf-8")

    errors = module.validate_outbox_recovery_contract(tmp_path)

    assert any("source-sensitive response field `payload`" in error for error in errors)


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/outbox_recovery_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_recovery_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
