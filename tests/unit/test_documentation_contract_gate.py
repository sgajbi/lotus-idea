from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "documentation_contract_gate.py"
    spec = importlib.util.spec_from_file_location("documentation_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_documentation_contract_gate_passes_current_repository_truth() -> None:
    module = _load_gate()

    assert module.validate_documentation_contract() == []


def test_documentation_contract_gate_blocks_missing_surface(tmp_path: Path) -> None:
    module = _load_gate()
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: required documentation surface is missing"]


def test_documentation_contract_gate_blocks_thin_surface(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nProduct Boundary\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        3,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: has 2 non-empty lines; minimum is 3"]


def test_documentation_contract_gate_blocks_missing_anchor(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nBoundary\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: missing required fragment `Product Boundary`"]


def test_documentation_contract_gate_blocks_placeholder_text(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nProduct Boundary\nTODO: fill later\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: contains placeholder text `TODO`"]


def test_documentation_contract_gate_blocks_unpolished_operator_doc(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "implementation-proof-readiness.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Implementation Proof Readiness\n\n"
        "This endpoint reports readiness.\n\n"
        "## Evidence\n\n"
        "Run the tests.\n",
        encoding="utf-8",
    )
    surface = module.PolishedDocumentationSurface(
        "docs/operations/implementation-proof-readiness.md",
        ("## What It Proves", "## Evidence"),
        1,
        1,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(surface,),
    )

    assert errors == [
        "docs/operations/implementation-proof-readiness.md: missing polished heading `## What It Proves`",
        "docs/operations/implementation-proof-readiness.md: has 0 markdown tables; minimum is 1",
        "docs/operations/implementation-proof-readiness.md: has 0 code fences; minimum is 1",
    ]


def test_documentation_contract_gate_accepts_polished_operator_doc(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "implementation-proof-readiness.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Implementation Proof Readiness\n\n"
        "| Field | Current Truth |\n"
        "| --- | --- |\n"
        "| Status | Certified internal diagnostic |\n\n"
        "## What It Proves\n\n"
        "It proves the aggregate readiness posture.\n\n"
        "## Evidence\n\n"
        "```powershell\n"
        "make implementation-proof-readiness-check\n"
        "```\n",
        encoding="utf-8",
    )
    surface = module.PolishedDocumentationSurface(
        "docs/operations/implementation-proof-readiness.md",
        ("## What It Proves", "## Evidence"),
        1,
        1,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(surface,),
    )

    assert errors == []
