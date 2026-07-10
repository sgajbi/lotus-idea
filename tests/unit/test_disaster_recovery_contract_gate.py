from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def test_disaster_recovery_contract_covers_every_migrated_idea_table() -> None:
    module = load_gate()

    assert module.validate_disaster_recovery_contract() == []


def test_disaster_recovery_contract_rejects_false_certification_and_weak_backup_policy(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["certification_status"] = "certified"
    payload["backup_and_pitr"]["logical_dump_is_pitr_proof"] = True
    payload["evidence_requirements"]["real_restored_backup_required"] = False
    payload["recovery_objectives"]["rpo_measurement"] = "backup_age"

    errors = validate_payload(module, tmp_path, payload)

    assert "disaster recovery header certification_status must be 'not_certified'" in errors
    assert "disaster recovery backup policy logical_dump_is_pitr_proof must be False" in errors
    assert (
        "disaster recovery evidence requirements real_restored_backup_required must be True"
        in errors
    )
    assert (
        "disaster recovery recovery objectives rpo_measurement must be "
        "'incident_cutoff_utc minus recovery_point_utc'"
    ) in errors


def test_disaster_recovery_contract_rejects_migration_inventory_drift(tmp_path: Path) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["restore_verification"]["owned_tables"].remove("idea_downstream_submission")

    errors = validate_payload(module, tmp_path, payload)

    assert (
        "disaster recovery owned_tables must exactly match idea tables declared by migrations"
        in errors
    )


def test_disaster_recovery_contract_rejects_weakened_representative_state_policy(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["restore_verification"]["required_non_empty_tables"].remove(
        "idea_outbox_recovery_audit"
    )
    payload["restore_verification"]["allowed_unvalidated_constraints"].append(
        "unreviewed_exception"
    )

    errors = validate_payload(module, tmp_path, payload)

    assert "disaster recovery representative-state table inventory drifted" in errors
    assert "disaster recovery unvalidated constraint exception inventory drifted" in errors


def test_disaster_recovery_contract_rejects_unsafe_sources_and_embedded_secrets(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = load_contract(module)
    payload["source_of_truth"]["migrations"] = "../migrations"
    payload["operating_model"]["connection"] = "postgresql://operator:secret@db/idea"

    errors = validate_payload(module, tmp_path, payload)

    assert "disaster recovery source migrations must be a safe relative path" in errors
    assert "disaster recovery contract must not embed credentials, DSNs, or secrets" in errors


def test_disaster_recovery_contract_reports_malformed_json(tmp_path: Path) -> None:
    module = load_gate()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("{", encoding="utf-8")

    errors = module.validate_disaster_recovery_contract(contract_path=contract_path)

    assert len(errors) == 1
    assert errors[0].startswith("disaster recovery contract is unreadable:")


def load_contract(module: ModuleType) -> dict[str, object]:
    return json.loads((ROOT / module.CONTRACT_PATH).read_text(encoding="utf-8"))


def validate_payload(module: ModuleType, tmp_path: Path, payload: dict[str, object]) -> list[str]:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    return module.validate_disaster_recovery_contract(contract_path=contract_path)


def load_gate() -> ModuleType:
    path = ROOT / "scripts/disaster_recovery_contract_gate.py"
    spec = importlib.util.spec_from_file_location("disaster_recovery_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
