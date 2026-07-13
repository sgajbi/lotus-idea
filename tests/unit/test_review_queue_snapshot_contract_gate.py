from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "review_queue_snapshot_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "review_queue_snapshot_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_review_queue_snapshot_contract_gate_passes_current_implementation() -> None:
    module = _load_gate()

    assert module.validate_review_queue_snapshot_contract(ROOT) == []


def test_review_queue_snapshot_contract_gate_rejects_missing_temporal_port_fields(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.CONTRACT_MODULES:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    port_path = tmp_path / module.PORT_MODULE
    port_path.write_text(
        port_path.read_text(encoding="utf-8").replace(
            "        evaluated_at_utc: datetime,\n",
            "",
            1,
        ),
        encoding="utf-8",
    )

    errors = module.validate_review_queue_snapshot_contract(tmp_path)

    assert any("must accept `evaluated_at_utc`" in error for error in errors)


def test_review_queue_snapshot_contract_gate_requires_rankable_policy_input(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.CONTRACT_MODULES:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    port_path = tmp_path / module.PORT_MODULE
    port_path.write_text(
        port_path.read_text(encoding="utf-8").replace(
            "        rankable_score_policy_versions: tuple[str, ...],\n",
            "",
            1,
        ),
        encoding="utf-8",
    )

    errors = module.validate_review_queue_snapshot_contract(tmp_path)

    assert any("must accept `rankable_score_policy_versions`" in error for error in errors)


def test_review_queue_snapshot_contract_gate_requires_policy_binding_in_snapshot(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    for relative_path in module.CONTRACT_MODULES:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    snapshot_path = tmp_path / module.DOMAIN_SNAPSHOT_MODULE
    snapshot_path.write_text(
        snapshot_path.read_text(encoding="utf-8").replace(
            '        "rankableScorePolicyVersions": normalized_score_policy_versions,\n',
            "",
        ),
        encoding="utf-8",
    )

    errors = module.validate_review_queue_snapshot_contract(tmp_path)

    assert any(
        "required snapshot contract `rankableScorePolicyVersions`" in error for error in errors
    )
