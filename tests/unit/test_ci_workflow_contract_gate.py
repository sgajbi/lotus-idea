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


def test_ci_contract_gate_blocks_mutable_merged_pr_main_releasability_ref(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '--ref "$dispatch_ref"',
            "--ref main",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "merged-pr-main-releasability.yml must not contain `--ref main`" in errors
    assert 'merged-pr-main-releasability.yml missing `--ref "$dispatch_ref"`' in errors


def test_ci_contract_gate_blocks_unguarded_immutable_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
            '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"',
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must guard immutable-ref lookup "
        "with an if/else reset before dispatch"
    ) in errors


def test_ci_contract_gate_blocks_trailing_command_after_dispatch_lookup_reset(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          else\n            existing_ref_sha=""\n          fi',
            (
                "          else\n"
                '            existing_ref_sha=""\n'
                '            gh api "repos/$GITHUB_REPOSITORY/actions/runs?per_page=1" >/dev/null\n'
                "          fi"
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must guard immutable-ref lookup "
        "with an if/else reset before dispatch"
    ) in errors


def test_ci_contract_gate_accepts_guarded_braced_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            "git/ref/tags/$dispatch_ref",
            "git/ref/tags/${dispatch_ref}",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert not [
        error for error in errors if error.startswith("merged-pr-main-releasability.yml must")
    ]


def test_ci_contract_gate_ignores_commented_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
            (
                "          # Lookup repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref "
                "before creating it.\n"
                '          if existing_ref_sha="$(gh api '
                '"repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" '
                '--jq .object.sha 2>/dev/null)"; then'
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert not [
        error for error in errors if error.startswith("merged-pr-main-releasability.yml must")
    ]


def test_ci_contract_gate_blocks_later_braced_unguarded_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          if [ -z "$existing_ref_sha" ]; then',
            (
                '          existing_ref_sha="$(gh api '
                '"repos/$GITHUB_REPOSITORY/git/ref/tags/${dispatch_ref}" '
                '--jq .object.sha 2>/dev/null)"\n'
                '          if [ -z "$existing_ref_sha" ]; then'
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must guard immutable-ref lookup "
        "with an if/else reset before dispatch"
    ) in errors


def test_ci_contract_gate_blocks_masked_dispatch_ref_lookup_fallback(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
            '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null || :)"',
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must not mask immutable-ref lookup "
        "failures with shell OR fallbacks"
    ) in errors


def test_ci_contract_gate_blocks_lookup_condition_suffix(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
            '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)" && false; then',
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must guard immutable-ref lookup "
        "with an if/else reset before dispatch"
    ) in errors


def test_ci_contract_gate_blocks_non_failing_dispatch_ref_mismatch_branch(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '              echo "::error::Dispatch ref $dispatch_ref points to $existing_ref_sha, expected $MERGE_COMMIT_SHA"\n              exit 1',
            '              echo "::error::Dispatch ref $dispatch_ref points to $existing_ref_sha, expected $MERGE_COMMIT_SHA"\n              :',
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must fail closed with exit 1 when "
        "an existing immutable dispatch ref points to a different SHA"
    ) in errors


def test_ci_contract_gate_blocks_function_scoped_dispatch_ref_mismatch_exit(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            '              echo "::error::Dispatch ref $dispatch_ref points to $existing_ref_sha, expected $MERGE_COMMIT_SHA"\n              exit 1',
            (
                '              echo "::error::Dispatch ref $dispatch_ref points to '
                '$existing_ref_sha, expected $MERGE_COMMIT_SHA"\n'
                "              collision_failure() {\n"
                "                exit 1\n"
                "              }"
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must fail closed with exit 1 when "
        "an existing immutable dispatch ref points to a different SHA"
    ) in errors


def test_ci_contract_gate_blocks_nested_dispatch_ref_mismatch_condition(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            (
                '            if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then\n'
                '              echo "::error::Dispatch ref $dispatch_ref points to '
                '$existing_ref_sha, expected $MERGE_COMMIT_SHA"\n'
                "              exit 1\n"
                "            fi"
            ),
            (
                "            if false; then\n"
                '              if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then\n'
                '                echo "::error::Dispatch ref $dispatch_ref points to '
                '$existing_ref_sha, expected $MERGE_COMMIT_SHA"\n'
                "                exit 1\n"
                "              fi\n"
                "            fi"
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must fail closed with exit 1 when "
        "an existing immutable dispatch ref points to a different SHA"
    ) in errors


def test_ci_contract_gate_blocks_subshell_masked_dispatch_ref_mismatch_exit(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            (
                '            if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then\n'
                '              echo "::error::Dispatch ref $dispatch_ref points to '
                '$existing_ref_sha, expected $MERGE_COMMIT_SHA"\n'
                "              exit 1\n"
                "            fi"
            ),
            (
                "            (\n"
                '              if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then\n'
                '                echo "::error::Dispatch ref $dispatch_ref points to '
                '$existing_ref_sha, expected $MERGE_COMMIT_SHA"\n'
                "                exit 1\n"
                "              fi\n"
                "            ) || true"
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must fail closed with exit 1 when "
        "an existing immutable dispatch ref points to a different SHA"
    ) in errors


def test_ci_contract_gate_blocks_unconditional_dispatch_ref_creation(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path)
    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            (
                '          if [ -z "$existing_ref_sha" ]; then\n'
                '            gh api "repos/$GITHUB_REPOSITORY/git/refs" \\\n'
                '              -f ref="refs/tags/$dispatch_ref" \\\n'
                '              -f sha="$MERGE_COMMIT_SHA" >/dev/null\n'
                "          fi"
            ),
            (
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" \\\n'
                '            -f ref="refs/tags/$dispatch_ref" \\\n'
                '            -f sha="$MERGE_COMMIT_SHA" >/dev/null'
            ),
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml must create the immutable dispatch ref only "
        "inside the empty existing-ref branch"
    ) in errors


def _copy_workflows(tmp_path: Path) -> Path:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    module = _load_ci_contract_gate()
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return workflow_dir
