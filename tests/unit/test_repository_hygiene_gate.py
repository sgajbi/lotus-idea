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


def test_repository_hygiene_gate_enforces_outbox_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "src/app/domain/outbox/delivery.py",
        "src/app/domain/outbox/events.py",
        "tests/unit/outbox/postgres_fake_helpers.py",
    }
    retired_paths = {
        "src/app/domain/events.py",
        "src/app/domain/outbox_delivery_state.py",
        "tests/unit/postgres_outbox_fake_helpers.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        "src/app/domain/events.py: legacy flat-module path must not be reintroduced",
        "src/app/domain/outbox/delivery.py: required bounded-module path is missing",
        "src/app/domain/outbox/events.py: required bounded-module path is missing",
        "src/app/domain/outbox_delivery_state.py: legacy flat-module path must not be reintroduced",
        "tests/unit/outbox/postgres_fake_helpers.py: required bounded-module path is missing",
        "tests/unit/postgres_outbox_fake_helpers.py: legacy flat-module path must not be reintroduced",
    ]


def test_repository_hygiene_gate_enforces_persistence_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    required_path = "src/app/infrastructure/persistence/candidate_mutation.py"
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - {required_path})

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [f"{required_path}: required bounded-module path is missing"]


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


def test_repository_hygiene_gate_allows_explicit_rfc_tracking_artifact() -> None:
    module = _load_repository_hygiene_gate()
    tracking_workflow = ".github/workflows/rfc-0002-closure.yml"

    violations = module.find_executable_naming_violations(
        [tracking_workflow, "contracts/rfc-0002-closure.json"],
        rfc_tracking_paths=frozenset({tracking_workflow}),
    )

    assert violations == []
