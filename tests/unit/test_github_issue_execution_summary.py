from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_summary() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_execution_summary.py"
    spec = importlib.util.spec_from_file_location(
        "github_issue_execution_summary",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_ledger_payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            (
                ROOT
                / "contracts"
                / "implementation-proof"
                / "rfc0002-github-issue-execution-ledger.v1.json"
            ).read_text(encoding="utf-8")
        ),
    )


def _write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_github_issue_execution_summary_reports_current_rfc0002_counts() -> None:
    module = _load_summary()

    summary = module.build_issue_execution_summary()

    assert summary["schemaVersion"] == "lotus-idea:rfc0002-github-issue-execution-summary:v1"
    assert summary["counts"]["total"] == 42
    assert summary["counts"]["open"] == 24
    assert summary["counts"]["closed"] == 18
    assert summary["counts"]["byExecutionStatus"]["open_in_progress"] == 1
    assert "open_fixed_local" not in summary["counts"]["byExecutionStatus"]
    assert "open_pr_raised" not in summary["counts"]["byExecutionStatus"]
    assert "open_merged_main_qa_pending" not in summary["counts"]["byExecutionStatus"]
    assert "open_ready" not in summary["counts"]["byExecutionStatus"]
    assert summary["counts"]["byExecutionStatus"]["open_pending_final_closure"] == 1
    assert summary["counts"]["byExecutionStatus"]["open_pending_post_completion"] == 1
    assert summary["counts"]["byExecutionStatus"]["open_blocked"] == 13
    assert summary["counts"]["byExecutionStatus"]["open_tracker"] == 8
    assert summary["counts"]["byExecutionStatus"]["closed_complete"] == 18
    assert summary["issuesByStatus"]["open_in_progress"] == [681]
    assert "open_fixed_local" not in summary["issuesByStatus"]
    assert "open_pr_raised" not in summary["issuesByStatus"]
    assert "open_merged_main_qa_pending" not in summary["issuesByStatus"]
    assert summary["issuesByStatus"]["open_pending_final_closure"] == [683]
    assert summary["issuesByStatus"]["open_pending_post_completion"] == [684]
    assert summary["issuesByStatus"]["open_blocked"] == [
        343,
        344,
        345,
        375,
        379,
        380,
        685,
        686,
        687,
        691,
        692,
        693,
        699,
    ]
    assert "open_ready" not in summary["issuesByStatus"]
    assert 681 in summary["issuesBySlice"]["slice-18"]
    assert summary["sourceOfTruth"]["liveGitHubAudit"] == (
        "make rfc0002-github-issue-execution-state-audit"
    )


def test_github_issue_execution_summary_markdown_is_comment_ready() -> None:
    module = _load_summary()

    rendered = module.render_markdown(module.build_issue_execution_summary())

    assert "# RFC-0002 GitHub Issue Execution Summary" in rendered
    assert "- Open issues: 24" in rendered
    assert "- Closed issues: 18" in rendered
    assert "## In-Progress Issues" in rendered
    assert "#681" in rendered
    assert "#681, #782" not in rendered
    assert "#681, #685" not in rendered
    assert "#756" not in rendered
    assert "## Fixed Locally Issues" in rendered
    assert "## Fixed Locally Issues\n\n_None._" in rendered
    assert "## PR-Open Issues" in rendered
    assert "## PR-Open Issues\n\n_None._" in rendered
    assert "## Merged-Main QA Pending Issues" in rendered
    assert "## Merged-Main QA Pending Issues\n\n_None._" in rendered
    assert "#379, #690" not in rendered
    assert "#340, #379" not in rendered
    assert "## Ready Issues" in rendered
    assert "## Ready Issues\n\n_None._" in rendered
    assert "## Pending Final Closure Issues\n\n#683" in rendered
    assert "## Pending Post-Completion Issues\n\n#684" in rendered
    assert "## Blocked Issues" in rendered
    assert (
        "#343, #344, #345, #375, #379, #380, #685, #686, #687, #691, #692, #693, #699"
    ) in rendered
    assert "Current issues: #340, #782" not in rendered
    assert "### `ai_attestation_and_model_governance`" in rendered
    assert "Current issues: _None._" in rendered
    assert "Current issues: #679, #699" in rendered
    assert "Current issues: #679, #696, #697, #699" not in rendered
    assert "_None._" in rendered
    assert "Run the live GitHub state audit" in rendered


def test_github_issue_execution_summary_fails_when_ledger_gate_fails(tmp_path: Path) -> None:
    module = _load_summary()
    ledger_payload = _load_ledger_payload()
    ledger_payload["issues"] = [
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] != 681
    ]

    broken_ledger = _write_json(tmp_path, "broken-ledger.json", ledger_payload)

    try:
        module.build_issue_execution_summary(ledger_path=broken_ledger)
    except ValueError as exc:
        assert "Missing RFC-0002 execution issue entries: #681" in str(exc)
    else:
        raise AssertionError("expected broken ledger to fail summary generation")
