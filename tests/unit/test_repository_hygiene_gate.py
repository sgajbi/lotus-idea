from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_repository_hygiene_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "repository_hygiene_gate.py"
    spec = importlib.util.spec_from_file_location("repository_hygiene_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_hygiene_gate_passes_current_tracked_files() -> None:
    module = _load_repository_hygiene_gate()
    tracked_paths = module._tracked_paths()

    assert module.find_repository_hygiene_violations(tracked_paths) == []
    assert module.find_bounded_module_placement_violations(tracked_paths) == []
    assert module.find_executable_naming_violations(tracked_paths) == []


def test_repository_hygiene_gate_blocks_python_cache_artifacts() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            "src/app/__pycache__/main.cpython-313.pyc",
            "tests/unit/test_example.py",
        ]
    )

    assert violations == [
        "src/app/__pycache__/main.cpython-313.pyc: "
        "generated or dependency directory content must not be tracked"
    ]


def test_repository_hygiene_gate_blocks_local_env_and_coverage_artifacts() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            ".env",
            "coverage.xml",
            "quality/quality_scorecard.md",
        ]
    )

    assert violations == [
        ".env: generated or local-only artifact must not be tracked",
        "coverage.xml: generated or local-only artifact must not be tracked",
    ]


def test_repository_hygiene_gate_blocks_build_outputs_and_databases() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            "build/lib/app.py",
            "dist/lotus_idea-0.1.0.tar.gz",
            "local/test.db",
        ]
    )

    assert violations == [
        "build/lib/app.py: generated or dependency directory content must not be tracked",
        "dist/lotus_idea-0.1.0.tar.gz: "
        "generated or dependency directory content must not be tracked",
        "local/test.db: generated or local-only file type must not be tracked",
    ]


def test_repository_hygiene_gate_enforces_lifecycle_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    tracked_paths = sorted(
        module.REQUIRED_BOUNDED_MODULE_PATHS - {"src/app/domain/data_lifecycle/authority.py"}
        | {"src/app/domain/lifecycle_authority.py"}
    )

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        "src/app/domain/data_lifecycle/authority.py: required bounded-module path is missing",
        "src/app/domain/lifecycle_authority.py: legacy flat-module path must not be reintroduced",
    ]


def test_repository_hygiene_gate_rejects_rfc_coupled_executable_names() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_executable_naming_violations(
        [
            "scripts/rfc_0002_validator.py",
            "tests/unit/test_slice_06_lifecycle.py",
            "docs/rfcs/RFC-0002-slice-06.md",
        ]
    )

    assert violations == [
        "scripts/rfc_0002_validator.py: executable artifact must be named for its capability, "
        "not an RFC or slice",
        "tests/unit/test_slice_06_lifecycle.py: executable artifact must be named for its "
        "capability, not an RFC or slice",
    ]
