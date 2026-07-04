from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "operator_workflows_operations_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "operator_workflows_operations_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _current_payload(module: ModuleType) -> dict[str, Any]:
    return cast("dict[str, Any]", module._load_contract(ROOT, module.CONTRACT_PATH))


def test_operator_workflows_operations_contract_gate_passes_current_contract() -> None:
    module = _load_gate()

    assert module.validate_operator_workflows_operations_contract() == []


def test_operator_workflows_operations_contract_gate_cli_reports_success(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_gate()
    monkeypatch.setattr(sys, "argv", ["operator_workflows_operations_contract_gate.py"])

    assert module.main() == 0

    assert "Operator workflows operations contract gate passed" in capsys.readouterr().out


def test_operator_workflows_operations_contract_gate_blocks_overclaiming() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["supportability_status"] = "supported"
    payload["supported_feature_promoted"] = True
    payload["dashboard_certified"] = False
    payload["alert_certified"] = False
    payload["operator_dashboard_controls"][0]["certification_status"] = "not_certified"

    errors = module.validate_operator_workflows_operations_contract_payload(payload)

    assert (
        "operator workflows operations contract supportability_status must be 'not_certified'"
        in errors
    )
    assert "operator workflows operations contract supported_feature_promoted must be False" in (
        errors
    )
    assert "operator workflows operations contract dashboard_certified must be True" in errors
    assert "operator workflows operations contract alert_certified must be True" in errors
    assert any("certification_status must be certified" in error for error in errors)


def test_operator_workflows_operations_contract_gate_blocks_control_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    control = payload["operator_dashboard_controls"][0]
    control["control_id"] = "local-dashboard"
    control["implemented_metric_family"] = "local_metric"
    control["required_operations"] = ["local_operation"]
    control["required_labels"] = ["operation", "portfolio_id"]
    payload["operator_alert_candidates"] = []

    errors = module.validate_operator_workflows_operations_contract_payload(payload)

    assert any("missing dashboard controls" in error for error in errors)
    assert any("unsupported dashboard controls: local-dashboard" in error for error in errors)
    assert any("implemented_metric_family" in error for error in errors)
    assert any("unsupported operations: local_operation" in error for error in errors)
    assert any("unsupported labels: portfolio_id" in error for error in errors)
    assert any("sensitive labels: portfolio_id" in error for error in errors)
    assert any("missing alert candidates" in error for error in errors)


def test_operator_workflows_operations_contract_gate_blocks_bad_source_truth() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_of_truth"] = {
        "operation_metric_contract": "missing.json",
        "contract_gate": "../outside.py",
    }

    errors = module.validate_operator_workflows_operations_contract_payload(payload)

    assert any("source_of_truth missing keys" in error for error in errors)
    assert any("operation_metric_contract path missing" in error for error in errors)
    assert any("contract_gate path must stay relative" in error for error in errors)


def test_operator_workflows_operations_contract_gate_blocks_source_authority_policy_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_authority_policy"] = {
        "label_source": "local",
        "aggregate_label": "portfolio-owned",
        "governed_labels": ["lotus-idea", "client-123"],
    }

    errors = module.validate_operator_workflows_operations_contract_payload(payload)

    assert any("source authority label source drifted" in error for error in errors)
    assert any("aggregate source authority drifted" in error for error in errors)
    assert any("OPERATION_EVENT_SOURCE_AUTHORITIES" in error for error in errors)


def test_operator_workflows_operations_contract_loader_rejects_non_object_file(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    try:
        module._load_contract(tmp_path, Path("contract.json"))
    except ValueError as exc:
        assert str(exc) == "operator workflows operations contract must be a JSON object"
    else:
        raise AssertionError("expected non-object contract file to fail")


def test_operator_workflows_operations_contract_gate_rejects_malformed_sections() -> None:
    module = _load_gate()
    payload = _current_payload(module)

    malformed_controls = json.loads(json.dumps(payload))
    malformed_controls["operator_dashboard_controls"] = {}
    assert module.validate_operator_workflows_operations_contract_payload(malformed_controls) == [
        "operator workflows operations contract dashboard controls must be a list"
    ]

    malformed_alerts = json.loads(json.dumps(payload))
    malformed_alerts["operator_alert_candidates"] = {}
    assert module.validate_operator_workflows_operations_contract_payload(malformed_alerts) == [
        "operator workflows operations contract alert candidates must be a list"
    ]
