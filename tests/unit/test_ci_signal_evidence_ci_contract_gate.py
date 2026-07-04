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


def test_ci_contract_gate_blocks_missing_feature_signal_evidence(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path, module)
    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace(
            "python scripts/ci_signal_evidence.py --jobs-json ci-jobs.json "
            "--output ci-signal-evidence.json",
            "python -m json.tool ci-jobs.json",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml missing `scripts/ci_signal_evidence.py`" in errors


def test_ci_contract_gate_blocks_unquoted_ci_signal_evidence_api_path(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path, module)
    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace(
            'gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs"',
            "gh api repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "feature-lane.yml missing "
        '`gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs"`'
    ) in errors
    assert (
        "feature-lane.yml must not contain "
        "`gh api repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs`"
    ) in errors


def test_ci_contract_gate_blocks_missing_main_release_evidence_reference(
    tmp_path: Path,
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = _copy_workflows(tmp_path, module)
    main_releasability = workflow_dir / "main-releasability.yml"
    main_releasability.write_text(
        main_releasability.read_text(encoding="utf-8").replace(
            '"ci_signal_evidence_path": "ci-signal-evidence.json",',
            "",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        'main-releasability.yml missing `"ci_signal_evidence_path": "ci-signal-evidence.json"`'
    ) in errors


def _copy_workflows(tmp_path: Path, module: ModuleType) -> Path:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return workflow_dir
