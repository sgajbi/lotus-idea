from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "incident_response_contract_gate.py"
    spec = importlib.util.spec_from_file_location("incident_response_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _current_payload(module: ModuleType) -> dict[str, Any]:
    return cast("dict[str, Any]", module._load_contract(ROOT, module.CONTRACT_PATH))


def test_incident_response_contract_gate_passes_current_contract() -> None:
    module = _load_gate()

    assert module.validate_incident_response_contract() == []


def test_incident_response_contract_gate_cli_reports_success(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_gate()
    monkeypatch.setattr(sys, "argv", ["incident_response_contract_gate.py"])

    assert module.main() == 0

    assert "Incident response contract gate passed" in capsys.readouterr().out


def test_incident_response_contract_gate_blocks_overclaiming() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["production_incident_certification_status"] = "certified"
    payload["supported_feature_promoted"] = True

    errors = module.validate_incident_response_contract_payload(payload)

    assert (
        "incident response contract production_incident_certification_status must be 'not_certified'"
        in errors
    )
    assert "incident response contract supported_feature_promoted must be False" in errors


def test_incident_response_contract_gate_blocks_missing_operating_model() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["severity_classes"] = payload["severity_classes"][:1]
    payload["incident_response_flow"] = ["detect", "recover"]
    payload["escalation_roles"] = []

    errors = module.validate_incident_response_contract_payload(payload)

    assert any("missing severity_classes" in error for error in errors)
    assert any("incident_response_flow must match governed" in error for error in errors)
    assert any("missing escalation_roles" in error for error in errors)


def test_incident_response_contract_gate_blocks_unsafe_evidence_policy() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    policy = payload["source_safe_evidence_policy"]
    policy["prohibited_content"] = ["tenant id"]
    policy["github_tracking_required"] = False

    errors = module.validate_incident_response_contract_payload(payload)

    assert (
        "incident response contract source_safe_evidence_policy.github_tracking_required must be true"
        in errors
    )
    assert "incident response evidence policy must prohibit secret" in errors
    assert "incident response evidence policy must prohibit DSN" in errors
    assert "incident response evidence policy must prohibit authorization header" in errors
    assert "incident response evidence policy must prohibit raw source payload" in errors


def test_incident_response_contract_gate_blocks_problem_management_drift() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    problem = payload["post_incident_problem_management"]
    problem["github_tracking_required"] = False
    problem["required_questions"] = []
    problem["required_action_families"] = []

    errors = module.validate_incident_response_contract_payload(payload)

    assert (
        "incident response contract post_incident_problem_management.github_tracking_required must be true"
        in errors
    )
    assert any(
        "incident response problem questions missing required values" in error for error in errors
    )
    assert any(
        "incident response action families missing required values" in error for error in errors
    )


def test_incident_response_contract_loader_rejects_non_object_file(tmp_path: Path) -> None:
    module = _load_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    try:
        module._load_contract(tmp_path, Path("contract.json"))
    except ValueError as exc:
        assert str(exc) == "incident response contract must be a JSON object"
    else:
        raise AssertionError("expected non-object contract file to fail")


def test_incident_response_contract_gate_rejects_bad_source_truth() -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_of_truth"] = {
        "contract": "missing.json",
        "contract_gate": "../outside.py",
    }

    errors = module.validate_incident_response_contract_payload(payload)

    assert any("source_of_truth missing keys" in error for error in errors)
    assert any("source_of_truth.contract path missing" in error for error in errors)
    assert any("source_of_truth.contract_gate path must stay relative" in error for error in errors)


def test_incident_response_contract_gate_rejects_doc_link_drift(tmp_path: Path) -> None:
    module = _load_gate()
    payload = _current_payload(module)
    payload["source_of_truth"] = dict(payload["source_of_truth"])
    payload["source_of_truth"]["incident_runbook"] = "docs/runbooks/incident-response.md"
    runbook_path = tmp_path / "docs" / "runbooks" / "incident-response.md"
    runbook_path.parent.mkdir(parents=True)
    runbook_path.write_text("# Incident Response\n\nmissing governed sections\n", encoding="utf-8")

    errors = module.validate_incident_response_contract_payload(
        json.loads(json.dumps(payload)),
        repository_root=tmp_path,
    )

    assert any(
        "incident-response.md: missing required incident response fragment" in error
        for error in errors
    )
