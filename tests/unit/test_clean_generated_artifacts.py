from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_clean_generated_artifacts() -> ModuleType:
    script_path = ROOT / "scripts" / "clean_generated_artifacts.py"
    spec = importlib.util.spec_from_file_location("clean_generated_artifacts", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cleanup_plan_includes_generated_python_and_test_artifacts(
    tmp_path: Path,
) -> None:
    module = _load_clean_generated_artifacts()
    generated_directory = tmp_path / "src" / "app" / "__pycache__"
    generated_directory.mkdir(parents=True)
    generated_file = generated_directory / "main.cpython-313.pyc"
    generated_file.write_bytes(b"bytecode")
    coverage_file = tmp_path / ".coverage.unit"
    coverage_file.write_text("coverage", encoding="utf-8")
    sbom_file = tmp_path / "sbom.cdx.json"
    sbom_file.write_text("{}", encoding="utf-8")

    plan = module.build_cleanup_plan(tmp_path)

    assert plan.directories == (generated_directory,)
    assert plan.files == (coverage_file, sbom_file)


def test_cleanup_removes_generated_artifacts_without_pruned_directories(
    tmp_path: Path,
) -> None:
    module = _load_clean_generated_artifacts()
    generated_directory = tmp_path / "tests" / "__pycache__"
    generated_directory.mkdir(parents=True)
    (generated_directory / "test_example.cpython-313.pyc").write_bytes(b"bytecode")
    local_artifact = tmp_path / "coverage.xml"
    local_artifact.write_text("<coverage />", encoding="utf-8")
    venv_cache = tmp_path / ".venv" / "Lib" / "__pycache__"
    venv_cache.mkdir(parents=True)
    venv_marker = venv_cache / "dependency.cpython-313.pyc"
    venv_marker.write_bytes(b"dependency bytecode")

    plan = module.clean_generated_artifacts(tmp_path)

    assert plan.directories == (generated_directory,)
    assert plan.files == (local_artifact,)
    assert not generated_directory.exists()
    assert not local_artifact.exists()
    assert venv_marker.exists()
