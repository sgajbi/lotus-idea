from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "source_temporal_contract_gate.py"
    spec = importlib.util.spec_from_file_location("source_temporal_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_temporal_contract_gate_passes_current_domain() -> None:
    module = _load_gate()

    assert module.validate_source_temporal_contract(ROOT) == []


def test_source_temporal_contract_gate_blocks_signal_without_shared_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.SIGNAL_DOMAIN_MODULES:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "def evaluate_signal(source_input):\n    return source_input\n",
            encoding="utf-8",
        )
    source_temporal_path = tmp_path / module.SOURCE_TEMPORAL_MODULE
    source_temporal_path.parent.mkdir(parents=True, exist_ok=True)
    source_temporal_path.write_text(
        "def source_temporal_violation():\n    return None\n",
        encoding="utf-8",
    )

    errors = module.validate_source_temporal_contract(tmp_path)

    assert len(errors) == len(module.SIGNAL_DOMAIN_MODULES)
    assert all("must call `temporal_blocked_signal_result`" in error for error in errors)
