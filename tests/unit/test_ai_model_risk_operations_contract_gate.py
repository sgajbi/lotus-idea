from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ai_model_risk_operations_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "ai_model_risk_operations_contract_gate",
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


def test_ai_model_risk_operations_contract_gate_passes_current_contract() -> None:
    module = _load_gate()

    assert module.validate_ai_model_risk_operations_contract() == []


def test_ai_model_risk_operations_contract_gate_cli_reports_success(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_gate()
    monkeypatch.setattr(sys, "argv", ["ai_model_risk_operations_contract_gate.py"])

    assert module.main() == 0

    assert "AI model-risk operations contract gate passed" in capsys.readouterr().out


def test_ai_model_risk_operations_contract_gate_blocks_product_promotion_and_uncertified_artifacts() -> (
    None
):
    module = _load_gate()
    payload = _current_payload(module)
    payload["supportability_status"] = "supported"
    payload["supported_feature_promoted"] = True
    payload["dashboard_certified"] = False
    payload["alert_certified"] = False
    payload["model_risk_dashboard_controls"][0]["certification_status"] = "not_certified"
    payload["model_risk_alert_candidates"][0]["certification_status"] = "not_certified"

    errors = module.validate_ai_model_risk_operations_contract_payload(payload)

    assert (
        "AI model-risk operations contract supportability_status must be 'not_certified'" in errors
    )
    assert "AI model-risk operations contract supported_feature_promoted must be False" in errors
    assert "AI model-risk operations contract dashboard_certified must be True" in errors
    assert "AI model-risk operations contract alert_certified must be True" in errors
    assert any("certification_status must be certified" in error for error in errors)


def test_ai_model_risk_operations_contract_gate_blocks_control_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    control = payload["model_risk_dashboard_controls"][0]
    control["control_id"] = "local-dashboard"
    control["implemented_metric_family"] = "local_metric"
    control["required_operations"] = ["local_operation"]
    control["required_labels"] = ["operation", "portfolio_id"]
    payload["model_risk_alert_candidates"] = []

    errors = module.validate_ai_model_risk_operations_contract_payload(payload)

    assert any("missing dashboard controls" in error for error in errors)
    assert any("unsupported dashboard controls: local-dashboard" in error for error in errors)
    assert any("implemented_metric_family" in error for error in errors)
    assert any("unsupported operations: local_operation" in error for error in errors)
    assert any("unsupported labels: portfolio_id" in error for error in errors)
    assert any("sensitive labels: portfolio_id" in error for error in errors)
    assert any("missing alert candidates" in error for error in errors)


def test_ai_model_risk_operations_contract_gate_blocks_action_policy_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["action_content_policy_version"] = "local-policy"
    payload["action_content_policy"]["accepted_label_posture"] = "provider_authored"
    payload["action_content_policy"]["raw_rejected_label_returned"] = True

    errors = module.validate_ai_model_risk_operations_contract_payload(payload)

    assert any("action_content_policy_version" in error for error in errors)
    assert "AI model-risk action_content_policy must match code-owned safety posture" in errors


def test_ai_model_risk_operations_contract_gate_blocks_output_integrity_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["output_integrity_version"] = "local-integrity"
    payload["output_content_integrity"]["persisted_content"] = "raw_provider_output"

    errors = module.validate_ai_model_risk_operations_contract_payload(payload)

    assert any("output_integrity_version" in error for error in errors)
    assert "AI model-risk output_content_integrity must match code-owned audit posture" in errors


def test_ai_model_risk_operations_contract_gate_blocks_bad_source_truth() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_of_truth"] = {
        "ai_readiness_source": "missing.py",
        "contract_gate": "../outside.py",
    }

    errors = module.validate_ai_model_risk_operations_contract_payload(payload)

    assert any("source_of_truth missing keys" in error for error in errors)
    assert (
        "AI model-risk operations contract source_of_truth.ai_readiness_source path missing"
        in errors
    )
    assert (
        "AI model-risk operations contract source_of_truth.contract_gate path must stay relative"
        in errors
    )


def test_ai_model_risk_operations_contract_loader_rejects_non_object_file(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    try:
        module._load_contract(tmp_path, Path("contract.json"))
    except ValueError as exc:
        assert str(exc) == "AI model-risk operations contract must be a JSON object"
    else:
        raise AssertionError("expected non-object contract file to fail")


def test_ai_model_risk_operations_contract_gate_rejects_malformed_sections() -> None:
    module = _load_gate()
    payload = _current_payload(module)

    malformed_controls = json.loads(json.dumps(payload))
    malformed_controls["model_risk_dashboard_controls"] = {}
    assert module.validate_ai_model_risk_operations_contract_payload(malformed_controls) == [
        "AI model-risk operations contract dashboard controls must be a list"
    ]

    malformed_alerts = json.loads(json.dumps(payload))
    malformed_alerts["model_risk_alert_candidates"] = {}
    assert module.validate_ai_model_risk_operations_contract_payload(malformed_alerts) == [
        "AI model-risk operations contract alert candidates must be a list"
    ]
