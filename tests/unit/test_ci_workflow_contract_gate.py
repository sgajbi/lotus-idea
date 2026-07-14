from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_blocks_duplicate_main_releasability_push_trigger(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    main_releasability = workflow_dir / "main-releasability.yml"
    main_releasability.write_text(
        main_releasability.read_text(encoding="utf-8").replace(
            "  workflow_dispatch:",
            '  push:\n    branches: [ "main" ]\n  workflow_dispatch:',
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "main-releasability.yml must not contain `  push:`" in errors


def test_ci_contract_gate_blocks_raw_pr_coverage_enforcement(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    pr_merge_gate = workflow_dir / "pr-merge-gate.yml"
    pr_merge_gate.write_text(
        pr_merge_gate.read_text(encoding="utf-8").replace(
            "make coverage-gate COVERAGE_DATA_DIR=coverage-data",
            "./.venv/bin/python -m coverage report --fail-under=99",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "pr-merge-gate.yml missing `make coverage-gate COVERAGE_DATA_DIR=coverage-data`"
    ) in errors
    assert "pr-merge-gate.yml must not contain `coverage report --fail-under=99`" in errors


def test_ci_contract_gate_blocks_raw_main_coverage_combine(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    main_releasability = workflow_dir / "main-releasability.yml"
    main_releasability.write_text(
        main_releasability.read_text(encoding="utf-8").replace(
            "make coverage-gate COVERAGE_DATA_DIR=coverage-data",
            "./.venv/bin/python -m coverage combine coverage-data",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "main-releasability.yml missing `make coverage-gate COVERAGE_DATA_DIR=coverage-data`"
    ) in errors
    assert "main-releasability.yml must not contain `coverage combine coverage-data`" in errors


def test_ci_contract_gate_requires_receipt_bound_durable_repository_proof(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    main_releasability = workflow_dir / "main-releasability.yml"
    main_releasability.write_text(
        main_releasability.read_text(encoding="utf-8").replace(
            "make durable-repository-ci-proof",
            "echo skipped durable repository proof",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "main-releasability.yml missing `make durable-repository-ci-proof`" in errors


def _copy_workflows(tmp_path: Path) -> Path:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    module = _load_ci_contract_gate()
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return workflow_dir
