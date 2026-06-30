from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def test_private_import_boundary_gate_passes_current_repository() -> None:
    module = _load_gate()

    assert module.validate_private_import_boundaries(ROOT) == []


def test_private_import_boundary_gate_blocks_cross_module_private_import(tmp_path: Path) -> None:
    module = _load_gate()
    domain_module = tmp_path / "src" / "app" / "domain" / "source_module.py"
    route_module = tmp_path / "src" / "app" / "api" / "consumer.py"
    domain_module.parent.mkdir(parents=True)
    route_module.parent.mkdir(parents=True)
    domain_module.write_text("def _private_helper() -> None:\n    pass\n", encoding="utf-8")
    route_module.write_text(
        "from app.domain.source_module import _private_helper\n",
        encoding="utf-8",
    )

    errors = module.validate_private_import_boundaries(tmp_path)

    assert errors == [
        "src/app/api/consumer.py:1: private import `_private_helper` from "
        "`app.domain.source_module` must use a public domain API"
    ]


def test_private_import_boundary_gate_allows_public_imports(tmp_path: Path) -> None:
    module = _load_gate()
    route_module = tmp_path / "src" / "app" / "api" / "consumer.py"
    route_module.parent.mkdir(parents=True)
    route_module.write_text(
        "from app.domain.source_module import public_helper\n",
        encoding="utf-8",
    )

    assert module.validate_private_import_boundaries(tmp_path) == []


def test_private_import_boundary_gate_does_not_overreach_application_helpers(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    route_module = tmp_path / "tests" / "unit" / "test_application_helper.py"
    route_module.parent.mkdir(parents=True)
    route_module.write_text(
        "from app.application.proof_helpers import _legacy_private_helper\n",
        encoding="utf-8",
    )

    assert module.validate_private_import_boundaries(tmp_path) == []


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "private_import_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("private_import_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
