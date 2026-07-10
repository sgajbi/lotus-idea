from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def test_supported_feature_promotion_contract_gate_passes_current_wiring() -> None:
    module = load_gate()

    assert module.validate_supported_feature_promotion_contract() == []


def test_supported_feature_promotion_contract_gate_rejects_status_counter_and_projection_drift(
    tmp_path: Path,
) -> None:
    module = load_gate()
    for relative_path in (*module.REQUIRED_CALLERS, *module.TRUTHFUL_PROJECTIONS):
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    readiness_path = tmp_path / "src/app/application/implementation_proof_readiness.py"
    readiness_path.write_text(
        readiness_path.read_text(encoding="utf-8").replace(
            "evaluate_supported_feature_promotion(",
            "_supported_feature_count(",
            1,
        ),
        encoding="utf-8",
    )
    api_path = tmp_path / "src/app/api/implementation_proof_readiness.py"
    api_path.write_text(
        api_path.read_text(encoding="utf-8").replace(
            "supportedFeaturePromoted=snapshot.supported_features_promoted",
            "supportedFeaturePromoted=False",
        ),
        encoding="utf-8",
    )

    errors = module.validate_supported_feature_promotion_contract(tmp_path)

    assert any("must call evaluate_supported_feature_promotion" in error for error in errors)
    assert any("must not restore status-only feature counting" in error for error in errors)
    assert any("must project supportedFeaturePromoted" in error for error in errors)


def load_gate() -> ModuleType:
    path = ROOT / "scripts/supported_feature_promotion_contract_gate.py"
    spec = importlib.util.spec_from_file_location("supported_feature_promotion_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
