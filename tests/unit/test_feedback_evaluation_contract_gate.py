from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def test_feedback_evaluation_contract_gate_accepts_repository_contract() -> None:
    module = _load_gate()

    assert module.validate_feedback_evaluation_contract() == []


def test_feedback_evaluation_contract_gate_rejects_taxonomy_drift(tmp_path: Path) -> None:
    module = _load_gate()
    source = ROOT / module.CONTRACT_PATH
    target = tmp_path / module.CONTRACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    contract = json.loads(source.read_text(encoding="utf-8"))
    contract["taxonomy"]["allowedCombinations"]["useful"] = ["wrong_priority"]
    target.write_text(json.dumps(contract), encoding="utf-8")
    _copy_migration_artifacts(tmp_path, module)

    errors = module.validate_feedback_evaluation_contract(tmp_path)

    assert any("taxonomy.allowedCombinations" in error for error in errors)


def test_feedback_evaluation_contract_gate_rejects_production_mutation_authority(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    source = ROOT / module.CONTRACT_PATH
    target = tmp_path / module.CONTRACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    contract = json.loads(source.read_text(encoding="utf-8"))
    contract["offlineEvaluation"]["productionMutationAuthority"] = "automatic_policy_update"
    target.write_text(json.dumps(contract), encoding="utf-8")
    _copy_migration_artifacts(tmp_path, module)

    errors = module.validate_feedback_evaluation_contract(tmp_path)

    assert any("productionMutationAuthority" in error for error in errors)


def _copy_migration_artifacts(tmp_path: Path, module: ModuleType) -> None:
    for suffix in (".sql", ".rollback.sql"):
        relative = Path("migrations") / f"{module.EXPECTED_MIGRATION}{suffix}"
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts/feedback_evaluation_contract_gate.py"
    spec = importlib.util.spec_from_file_location("feedback_evaluation_contract_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
