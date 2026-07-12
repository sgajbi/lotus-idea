from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_foundation_structure_gate() -> ModuleType:
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.append(str(scripts_dir))
    script_path = scripts_dir / "foundation_structure_gate.py"
    spec = importlib.util.spec_from_file_location("foundation_structure_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_minimum_foundation_truth(root: Path) -> None:
    (root / "supported-features").mkdir(parents=True)
    (root / "supported-features" / "supported-features.json").write_text(
        json.dumps(
            {
                "current_posture": "foundation_only",
                "features": [],
                "planned_capabilities": [
                    {
                        "id": "candidate-lifecycle",
                        "name": "Candidate lifecycle",
                        "governing_rfc": "docs/rfcs/RFC-0002.md",
                        "status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    documents = {
        "README.md": ("foundation-only\nno externally supported product feature is promoted\n"),
        "REPOSITORY-ENGINEERING-CONTEXT.md": (
            "No externally supported product feature is promoted yet.\nmake foundation-structure-gate\n"
        ),
        "docs/rfcs/README.md": ("currently in foundation state\nFoundation structure gate\n"),
        "wiki/Supported-Features.md": (
            "Current posture: no business feature is supported yet.\n"
            "`current_posture` | `foundation_only`\n"
        ),
        "wiki/Validation-and-CI.md": ("make foundation-structure-gate\nRFC-0002 Slice 2\n"),
    }
    for relative_path, content in documents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_foundation_structure_gate_accepts_foundation_only_truth(tmp_path: Path) -> None:
    module = _load_foundation_structure_gate()
    _write_minimum_foundation_truth(tmp_path)

    assert module.validate_foundation_structure(tmp_path, architecture_violations=[]) == []


def test_foundation_structure_gate_blocks_supported_feature_promotion(tmp_path: Path) -> None:
    module = _load_foundation_structure_gate()
    _write_minimum_foundation_truth(tmp_path)
    payload_path = tmp_path / "supported-features" / "supported-features.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["features"] = [{"id": "unsupported-promotion"}]
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_foundation_structure(tmp_path, architecture_violations=[])

    assert "supported-features features[] must remain empty for the foundation posture" in errors


def test_foundation_structure_gate_blocks_missing_documentation_truth(tmp_path: Path) -> None:
    module = _load_foundation_structure_gate()
    _write_minimum_foundation_truth(tmp_path)
    (tmp_path / "README.md").write_text("service overview\n", encoding="utf-8")

    errors = module.validate_foundation_structure(tmp_path, architecture_violations=[])

    assert "README.md must contain `foundation-only`" in errors
    assert "README.md must contain `no externally supported product feature is promoted`" in errors


def test_foundation_structure_gate_reports_architecture_boundary_violations(tmp_path: Path) -> None:
    module = _load_foundation_structure_gate()
    _write_minimum_foundation_truth(tmp_path)

    errors = module.validate_foundation_structure(
        tmp_path,
        architecture_violations=[
            {
                "path": "src/app/domain/bad.py",
                "import": "pydantic",
                "layer": "domain",
                "module": "app.domain.bad",
                "rule": "Domain must stay framework-free.",
            }
        ],
    )

    assert errors == ["src/app/domain/bad.py imports pydantic across the domain boundary"]
