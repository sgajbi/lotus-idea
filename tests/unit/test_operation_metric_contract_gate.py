from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "operation_metric_contract_gate.py"
    spec = importlib.util.spec_from_file_location("operation_metric_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _current_payload(module: ModuleType) -> dict[str, Any]:
    return cast("dict[str, Any]", module._load_contract(ROOT, module.CONTRACT_PATH))


def test_operation_metric_contract_gate_passes_current_contract() -> None:
    module = _load_gate()

    assert module.validate_operation_metric_contract() == []


def test_operation_metric_contract_gate_cli_reports_success(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_gate()
    monkeypatch.setattr(sys, "argv", ["operation_metric_contract_gate.py"])

    assert module.main() == 0

    assert "Operation metric contract gate passed" in capsys.readouterr().out


def test_operation_metric_contract_gate_blocks_premature_certification() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["supportability_status"] = "supported"
    payload["supported_feature_promoted"] = True
    payload["dashboard_certified"] = True
    payload["alert_certified"] = True
    payload["metrics"][0]["operations"][0]["supportability_status"] = "supported"

    errors = module.validate_operation_metric_contract_payload(payload)

    assert "operation metric contract supportability_status must be 'not_certified'" in errors
    assert "operation metric contract supported_feature_promoted must be False" in errors
    assert "operation metric contract dashboard_certified must be False" in errors
    assert "operation metric contract alert_certified must be False" in errors
    assert any("supported status is blocked until feature promotion" in error for error in errors)


def test_operation_metric_contract_gate_blocks_metric_label_and_operation_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    metric = payload["metrics"][0]
    metric["labels"] = ["operation", "portfolio_id"]
    metric["outcomes"] = ["accepted"]
    metric["operations"] = [
        {
            "operation": "unowned_operation",
            "scope": "",
            "source_authority": "lotus-idea",
            "supportability_status": "foundation_only",
        }
    ]

    errors = module.validate_operation_metric_contract_payload(payload)

    assert any("OPERATION_METRIC_LABELS" in error for error in errors)
    assert any("sensitive keys: portfolio_id" in error for error in errors)
    assert "operation metric outcomes must match code-owned OperationOutcome values" in errors
    assert any("scope is required" in error for error in errors)
    assert any("missing operations" in error for error in errors)
    assert any("unsupported operations: unowned_operation" in error for error in errors)


def test_operation_metric_contract_gate_blocks_source_authority_vocabulary_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["metrics"][0]["source_authorities"] = ["lotus-idea", "client-123"]

    errors = module.validate_operation_metric_contract_payload(payload)

    assert any("OPERATION_EVENT_SOURCE_AUTHORITIES" in error for error in errors)


def test_operation_metric_contract_gate_blocks_bad_source_truth_and_authority() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_of_truth"] = {
        "metric_source": "missing.py",
        "contract_gate": "../outside.py",
    }
    payload["metrics"][0]["operations"][0]["source_authority"] = "lotus-idea-local"

    errors = module.validate_operation_metric_contract_payload(payload)

    assert any("source_of_truth missing keys" in error for error in errors)
    assert "operation metric contract source_of_truth.metric_source path missing" in errors
    assert (
        "operation metric contract source_of_truth.contract_gate path must stay relative" in errors
    )
    assert any("source_authority is not a governed Lotus authority" in error for error in errors)


def test_operation_metric_contract_loader_rejects_non_object_file(tmp_path: Path) -> None:
    module = _load_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    try:
        module._load_contract(tmp_path, Path("contract.json"))
    except ValueError as exc:
        assert str(exc) == "operation metric contract must be a JSON object"
    else:
        raise AssertionError("expected non-object contract file to fail")


def test_operation_metric_contract_gate_rejects_malformed_sections() -> None:
    module = _load_gate()
    payload = _current_payload(module)

    malformed_metrics = json.loads(json.dumps(payload))
    malformed_metrics["metrics"] = {}
    assert module.validate_operation_metric_contract_payload(malformed_metrics) == [
        "operation metric contract metrics must be a list"
    ]

    malformed_operations = json.loads(json.dumps(payload))
    malformed_operations["metrics"][0]["operations"] = {}
    assert (
        "operation metric operations must be a list"
        in module.validate_operation_metric_contract_payload(malformed_operations)
    )
