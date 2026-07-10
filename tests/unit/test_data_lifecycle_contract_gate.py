from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]


def test_data_lifecycle_contract_classifies_every_migrated_table() -> None:
    module = load_gate()

    assert module.validate_data_lifecycle_contract() == []


def test_data_lifecycle_contract_rejects_false_certification_and_weakened_controls(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["certification_status"] = "certified"
    payload["enforcement_controls"]["unknown_policy_fails_closed"] = False
    payload["enforcement_controls"]["dual_authorization_required_for_release_erasure_and_purge"] = (
        False
    )
    payload["authority_boundaries"]["idea_may_self_authorize_legal_hold_or_erasure"] = True

    errors = validate_payload(module, tmp_path, payload)

    assert "data lifecycle header certification_status must be 'not_certified'" in errors
    assert "data lifecycle controls unknown_policy_fails_closed must be True" in errors
    assert (
        "data lifecycle controls dual_authorization_required_for_release_erasure_and_purge "
        "must be True"
    ) in errors
    assert (
        "data lifecycle authorities idea_may_self_authorize_legal_hold_or_erasure must be False"
        in errors
    )


def test_data_lifecycle_contract_rejects_inventory_and_policy_drift(tmp_path: Path) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["record_inventory"].pop()
    payload["record_inventory"][0]["policy_ref"] = "lotus-idea:unknown:policy:v1"
    payload["retention_policies"][0]["duration"] = "forever"
    payload["accepted_external_policy_refs"] = {
        "caller-controlled-policy": payload["retention_policies"][0]["policy_ref"]
    }

    errors = validate_payload(module, tmp_path, payload)

    assert "data lifecycle record inventory must exactly match migrated idea tables" in errors
    assert "data lifecycle table idea_candidate_record references an unknown policy" in errors
    assert "data lifecycle policy duration must be a positive ISO year/day duration" in errors
    assert "data lifecycle accepted external policy references drifted" in errors


def test_data_lifecycle_contract_rejects_unsafe_sources_and_embedded_secrets(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["source_of_truth"]["migrations"] = "../migrations"
    payload["authority_boundaries"]["connection"] = "postgresql://operator:secret@db/idea"

    errors = validate_payload(module, tmp_path, payload)

    assert "data lifecycle source migrations must be a safe relative path" in errors
    assert "data lifecycle contract must not embed credentials, DSNs, or secrets" in errors


def test_data_lifecycle_contract_reports_malformed_json(tmp_path: Path) -> None:
    module = load_gate()
    path = tmp_path / "contract.json"
    path.write_text("{", encoding="utf-8")

    errors = module.validate_data_lifecycle_contract(contract_path=path)

    assert len(errors) == 1
    assert errors[0].startswith("data lifecycle contract is unreadable:")


def load_contract(module: ModuleType) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / module.CONTRACT_PATH).read_text(encoding="utf-8")),
    )


def validate_payload(module: ModuleType, tmp_path: Path, payload: dict[str, Any]) -> list[str]:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return cast(list[str], module.validate_data_lifecycle_contract(contract_path=path))


def load_gate() -> ModuleType:
    path = ROOT / "scripts/data_lifecycle_contract_gate.py"
    spec = importlib.util.spec_from_file_location("data_lifecycle_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
