from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _load_downstream_realization_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "downstream_realization_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "downstream_realization_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_downstream_realization_contract_gate_passes_current_contract_plan() -> None:
    module = _load_downstream_realization_contract_gate()

    assert module.validate_downstream_realization_contract_plan() == []


def test_downstream_realization_contract_gate_cli_reports_success(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_downstream_realization_contract_gate()
    monkeypatch.setattr(sys, "argv", ["downstream_realization_contract_gate.py"])

    assert module.main() == 0

    assert "Downstream realization contract gate passed" in capsys.readouterr().out


def test_downstream_realization_contract_gate_blocks_premature_certification() -> None:
    module = _load_downstream_realization_contract_gate()
    payload = _plan_payload(module.load_downstream_realization_contract_plan())
    payload["contract_version"] = "2.0.0"
    payload["lifecycle_status"] = "active"
    payload["supportability_status"] = "supported"
    payload["route_existence_proven"] = True
    payload["downstream_execution_proven"] = True
    payload["supported_feature_promoted"] = True
    plan = module._parse_payload(payload)

    errors = module.validate_downstream_realization_contract_plan_payload(plan)

    assert "downstream contract plan contract_version must be 1.0.0" in errors
    assert "downstream contract plan lifecycle_status must remain planned" in errors
    assert "downstream contract plan supportability_status must remain not_certified" in errors
    assert "downstream contract plan must not claim route existence proof" in errors
    assert "downstream contract plan must not claim downstream execution proof" in errors
    assert "downstream contract plan must not promote supported features" in errors


def test_downstream_realization_contract_gate_blocks_contract_drift() -> None:
    module = _load_downstream_realization_contract_gate()
    payload = _plan_payload(module.load_downstream_realization_contract_plan())
    payload["contracts"] = [
        {
            "contract_id": "lotus-idea-to-lotus-advise-proposal-intake:v1",
            "owner_repository": "lotus-idea",
            "source_authority": "lotus-idea",
            "target_route": "/api/v1/proposals",
            "route_fit_status": "certified",
            "adapter_status": "implemented",
            "evidence_refs": ["POST http://lotus-advise/api/v1/proposals"],
            "blockers": [],
        }
    ]
    plan = module._parse_payload(payload)

    errors = module.validate_downstream_realization_contract_plan_payload(plan)

    assert any("missing contracts" in error for error in errors)
    assert any("owner_repository must be lotus-advise" in error for error in errors)
    assert any("source_authority must be lotus-advise" in error for error in errors)
    assert any("target_route must remain planned" in error for error in errors)
    assert any("route_fit_status must remain not_certified" in error for error in errors)
    assert any("adapter_status must remain planned" in error for error in errors)
    assert any("blockers are required" in error for error in errors)
    assert any("evidence_refs missing required references" in error for error in errors)
    assert any("must not include downstream current routes" in error for error in errors)


def test_downstream_realization_contract_gate_blocks_missing_source_truth() -> None:
    module = _load_downstream_realization_contract_gate()
    current_plan = module.load_downstream_realization_contract_plan()
    payload = _plan_payload(current_plan)
    payload["source_of_truth"] = {
        "readiness_builder": "missing.py",
        "contract_loader": "../outside.py",
    }
    plan = module._parse_payload(payload)

    errors = module.validate_downstream_realization_contract_plan_payload(plan)

    assert any("source_of_truth missing keys" in error for error in errors)
    assert "downstream contract plan source_of_truth.readiness_builder path missing" in errors
    assert "downstream contract plan source_of_truth.contract_loader path must stay relative" in (
        errors
    )


def test_downstream_realization_contract_loader_rejects_non_object_file(tmp_path: Path) -> None:
    module = _load_downstream_realization_contract_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    try:
        module.load_downstream_realization_contract_plan(
            repository_root=tmp_path,
            contract_path=Path("contract.json"),
        )
    except ValueError as exc:
        assert str(exc) == "downstream realization contract plan must be a JSON object"
    else:
        raise AssertionError("expected non-object contract file to fail")


def test_downstream_realization_contract_loader_rejects_malformed_sections() -> None:
    module = _load_downstream_realization_contract_gate()
    payload = _plan_payload(module.load_downstream_realization_contract_plan())

    source_truth_payload = dict(payload)
    source_truth_payload["source_of_truth"] = []
    try:
        module._parse_payload(source_truth_payload)
    except ValueError as exc:
        assert str(exc) == "downstream realization source_of_truth must be an object"
    else:
        raise AssertionError("expected malformed source_of_truth to fail")

    contracts_payload = dict(payload)
    contracts_payload["contracts"] = {}
    try:
        module._parse_payload(contracts_payload)
    except ValueError as exc:
        assert str(exc) == "downstream realization contracts must be a list"
    else:
        raise AssertionError("expected malformed contracts to fail")

    contract_entries_payload = dict(payload)
    contract_entries_payload["contracts"] = ["not-object"]
    try:
        module._parse_payload(contract_entries_payload)
    except ValueError as exc:
        assert str(exc) == "downstream realization contract entries must be objects"
    else:
        raise AssertionError("expected malformed contract entry to fail")


def test_downstream_realization_contract_loader_coerces_non_list_contract_fields() -> None:
    module = _load_downstream_realization_contract_gate()
    payload = _plan_payload(module.load_downstream_realization_contract_plan())
    contract = dict(payload["contracts"][0])
    contract["evidence_refs"] = "not-list"
    contract["blockers"] = "not-list"
    payload["contracts"] = [contract]

    plan = module._parse_payload(payload)

    assert plan.contracts[0].evidence_refs == ()
    assert plan.contracts[0].blockers == ()


def _plan_payload(plan: Any) -> dict[str, Any]:
    return json.loads(
        json.dumps(
            {
                "contract_id": plan.contract_id,
                "contract_version": plan.contract_version,
                "repository": plan.repository,
                "lifecycle_status": plan.lifecycle_status,
                "supportability_status": plan.supportability_status,
                "route_existence_proven": plan.route_existence_proven,
                "downstream_execution_proven": plan.downstream_execution_proven,
                "supported_feature_promoted": plan.supported_feature_promoted,
                "source_of_truth": dict(plan.source_of_truth),
                "contracts": [
                    {
                        "contract_id": contract.contract_id,
                        "owner_repository": contract.owner_repository,
                        "source_authority": contract.source_authority,
                        "target_route": contract.target_route,
                        "route_fit_status": contract.route_fit_status,
                        "adapter_status": contract.adapter_status,
                        "evidence_refs": list(contract.evidence_refs),
                        "blockers": list(contract.blockers),
                    }
                    for contract in plan.contracts
                ],
            }
        )
    )
