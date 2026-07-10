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
    _copy_contract_files(module, tmp_path)
    response_target = tmp_path / "src/app/api/outbox_recovery_models.py"
    response_target.write_text("class UnsafeResponse:\n    payload: dict\n", encoding="utf-8")

    errors = module.validate_outbox_recovery_contract(tmp_path)

    assert any("source-sensitive response field `payload`" in error for error in errors)


def test_outbox_recovery_contract_gate_rejects_bounded_postgres_scan(tmp_path: Path) -> None:
    module = _load_gate()
    _copy_contract_files(module, tmp_path)
    postgres_target = tmp_path / "src/app/infrastructure/postgres_outbox_recovery.py"
    postgres_target.write_text(
        postgres_target.read_text(encoding="utf-8")
        + "\nMAX_DEAD_LETTER_RECOVERY_LOOKUP_ROWS = 1000\n",
        encoding="utf-8",
    )

    errors = module.validate_outbox_recovery_contract(tmp_path)

    assert "PostgreSQL recovery lookup must not impose an arbitrary row limit" in errors


def _copy_contract_files(module: ModuleType, target_root: Path) -> None:
    relative_paths = set(module.REQUIRED_FRAGMENTS) | {
        "src/app/api/outbox_recovery_models.py",
        "src/app/domain/events.py",
    }
    for relative_path in relative_paths:
        source = ROOT / relative_path
        target = target_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/outbox_recovery_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_recovery_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
