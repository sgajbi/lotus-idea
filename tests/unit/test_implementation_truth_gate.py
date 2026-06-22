from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "implementation_truth_gate.py"
    spec = importlib.util.spec_from_file_location("implementation_truth_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_implementation_truth_gate_passes_current_repository_truth() -> None:
    module = _load_gate()

    assert module.validate_implementation_truth() == []


def test_implementation_truth_gate_blocks_unqualified_demo_claim(tmp_path: Path) -> None:
    module = _load_gate()
    current_state = tmp_path / "README.md"
    current_state.write_text("Lotus Idea is demo-ready for opportunity intelligence.\n")

    errors = module.validate_implementation_truth(
        implemented_features_count=0,
        scan_paths=(current_state,),
    )

    assert errors == [
        f"{current_state}:1: unqualified current-state promotion claim `demo_ready` "
        "while no supported feature is implemented"
    ]


def test_implementation_truth_gate_allows_explicitly_blocked_claim(tmp_path: Path) -> None:
    module = _load_gate()
    current_state = tmp_path / "Demo-Readiness.md"
    current_state.write_text("Current posture: not demo-ready for business behavior.\n")

    assert (
        module.validate_implementation_truth(
            implemented_features_count=0,
            scan_paths=(current_state,),
        )
        == []
    )


def test_implementation_truth_gate_skips_after_supported_feature_promotion(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    current_state = tmp_path / "Supported-Features.md"
    current_state.write_text("Lotus Idea is demo-ready for a certified data product.\n")

    assert (
        module.validate_implementation_truth(
            implemented_features_count=1,
            scan_paths=(current_state,),
        )
        == []
    )
