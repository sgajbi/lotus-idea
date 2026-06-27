from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_outbox_consumer_contract_gate_accepts_repo_contract() -> None:
    module = _load_contract_gate_script()

    assert module.validate_outbox_consumer_contract() == []


def test_outbox_consumer_contract_gate_rejects_premature_runtime_certification(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    source_contract = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-consumers.v1.json"
    contract = json.loads(source_contract.read_text(encoding="utf-8"))
    contract["downstreamConsumerRuntimeProven"] = True
    contract["declaredConsumers"][0]["certificationStatus"] = "certified"
    contract_path = tmp_path / "lotus-idea-outbox-consumers.v1.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    errors = module.validate_outbox_consumer_contract(contract_path=contract_path)

    assert "downstreamConsumerRuntimeProven must remain false before live certification" in errors
    assert "declaredConsumers[0].certificationStatus must stay not runtime certified" in errors


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox_consumer_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_consumer_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
