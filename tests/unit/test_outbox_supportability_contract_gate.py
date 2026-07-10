from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def test_outbox_supportability_contract_gate_passes_current_contract() -> None:
    module = load_gate()

    assert module.validate_outbox_supportability_contract() == []


def test_outbox_supportability_contract_gate_rejects_threshold_and_label_drift(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = json.loads((ROOT / module.CONTRACT_PATH).read_text(encoding="utf-8"))
    payload["thresholds"]["delivery_ready_count"] = 1000
    payload["metric_families"][0]["labels"] = ["repository", "event_id"]
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_outbox_supportability_contract(contract_path=contract_path)

    assert "outbox supportability thresholds must match code-owned policy" in errors
    assert any("forbidden labels: event_id" in error for error in errors)


def load_gate() -> ModuleType:
    path = ROOT / "scripts/outbox_supportability_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_supportability_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
