from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
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
    ledger_payload = _load_ledger_payload()
    ledger_issues = [issue for issue in ledger_payload["issues"] if isinstance(issue, dict)]
    issue_681 = next(issue for issue in ledger_issues if issue["issueNumber"] == 681)
    issue_681_status = issue_681["executionStatus"]
    expected_github_counts = Counter(issue["githubState"] for issue in ledger_issues)
    expected_execution_counts = Counter(issue["executionStatus"] for issue in ledger_issues)

    summary = module.build_issue_execution_summary()

    assert summary["schemaVersion"] == "lotus-idea:rfc0002-github-issue-execution-summary:v1"
    assert summary["counts"]["total"] == len(ledger_issues)
    assert summary["counts"]["open"] == expected_github_counts["open"]
    assert summary["counts"]["closed"] == expected_github_counts["closed"]
    assert summary["counts"]["byExecutionStatus"] == dict(sorted(expected_execution_counts.items()))
    assert issue_681_status == "open_in_progress"
    assert "open_fixed_local" not in summary["counts"]["byExecutionStatus"]
    assert (
        summary["counts"]["byExecutionStatus"][issue_681_status]
        == expected_execution_counts[issue_681_status]
    )
    assert "open_merged_main_qa_pending" not in summary["counts"]["byExecutionStatus"]
    assert "open_ready" not in summary["counts"]["byExecutionStatus"]
    assert summary["counts"]["byExecutionStatus"]["open_pending_final_closure"] == 1
    assert summary["counts"]["byExecutionStatus"]["open_pending_post_completion"] == 1
    assert summary["counts"]["byExecutionStatus"]["open_blocked"] == 14
    assert summary["counts"]["byExecutionStatus"]["open_tracker"] == 8
    assert (
        summary["counts"]["byExecutionStatus"]["closed_complete"]
        == expected_execution_counts["closed_complete"]
    )
    assert summary["issuesByStatus"][issue_681_status] == [681]
    assert summary["issuesByStatus"]["open_in_progress"] == [681]
    assert summary["issuesByStatus"]["open_pr_raised"] == [854]
    assert "open_fixed_local" not in summary["issuesByStatus"]
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
        814,
    ]
    assert "open_ready" not in summary["issuesByStatus"]
    assert 681 in summary["issuesBySlice"]["slice-18"]
    assert 854 in summary["issuesBySlice"]["slice-18"]
    assert summary["sourceOfTruth"]["liveGitHubAudit"] == (
        "make rfc0002-github-issue-execution-state-audit"
    )


def test_issue_681_ledger_records_pr837_exact_main_evidence() -> None:
    ledger_payload = _load_ledger_payload()
    issue_681 = next(
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )
    evidence_notes = "\n".join(issue_681["evidenceSyncNotes"])

    assert "PR #837 merged the Workbench/Core classification sync" in evidence_notes
    assert "2f47c476855aa6ddc9bc8c5b359f85f023725e8f" in evidence_notes
    assert "30721884347" in evidence_notes
    assert "30721880898" in evidence_notes
    assert "sgajbi/lotus-workbench#500 is now closed" in evidence_notes
    assert "sgajbi/lotus-core#885" in evidence_notes


def test_issue_681_ledger_records_pr838_exact_main_evidence() -> None:
    ledger_payload = _load_ledger_payload()
    issue_681 = next(
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )
    evidence_notes = "\n".join(issue_681["evidenceSyncNotes"])

    assert "PR #838 merged to Idea main" in evidence_notes
    assert "2c2d35667643ad5efae83924475574ab6c16be03" in evidence_notes
    assert "30723235065" in evidence_notes
    assert "lotus-idea.wiki commit ee15dc3" in evidence_notes
    assert "#681 returned to open_in_progress/status/in-progress" in evidence_notes


def test_issue_681_ledger_records_pr839_exact_main_evidence() -> None:
    ledger_payload = _load_ledger_payload()
    issue_681 = next(
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )
    evidence_notes = "\n".join(issue_681["evidenceSyncNotes"])

    assert "PR #839 merged to Idea main" in evidence_notes
    assert "71867084c2832d053342db048557e03720a3773a" in evidence_notes
    assert "30724145516" in evidence_notes
    assert "91432087325" in evidence_notes
    assert "lotus-idea.wiki commit c2258e6" in evidence_notes
    assert "#681 returned to open_in_progress/status/in-progress" in evidence_notes


def test_issue_681_ledger_records_latest_exact_main_evidence() -> None:
    ledger_payload = _load_ledger_payload()
    issue_681 = next(
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )
    evidence_notes = "\n".join(issue_681["evidenceSyncNotes"])

    assert "PR #842 merged the PR #841 evidence-sync tranche" in evidence_notes
    assert "4e2dd20c3f1b7f17a30eda016e79c62e631b2a2f" in evidence_notes
    assert "30727100273" in evidence_notes
    assert "PR #843 merged the RFC-0002 posture snapshot documentation guard" in evidence_notes
    assert "2ed353b0394a625dd212b437fb93c0d5d4c02a89" in evidence_notes
    assert "30728039165" in evidence_notes
    assert "30728037050" in evidence_notes
    assert "lotus-idea.wiki commit 87dd4e4" in evidence_notes
    assert "PR #844 merged the PR #843 evidence synchronization" in evidence_notes
    assert "c21deeb55dcb1d46395c02c95053ab6149ef6ad6" in evidence_notes
    assert "30728738511" in evidence_notes
    assert "30728733346" in evidence_notes
    assert "lotus-idea.wiki commit b47cbcb" in evidence_notes
    assert "issuecomment-5154685336" in evidence_notes
    assert "#681 returned to open_in_progress/status/in-progress" in evidence_notes


def test_github_issue_execution_summary_markdown_is_comment_ready() -> None:
    module = _load_summary()
    ledger_payload = _load_ledger_payload()
    issue_681 = next(
        issue
        for issue in ledger_payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )
    section_by_status = {
        "open_in_progress": "## In-Progress Issues",
        "open_pr_raised": "## PR-Open Issues",
    }
    issue_681_section = section_by_status[issue_681["executionStatus"]]

    summary = module.build_issue_execution_summary()
    rendered = module.render_markdown(summary)

    assert "# RFC-0002 GitHub Issue Execution Summary" in rendered
    assert f"- Open issues: {summary['counts']['open']}" in rendered
    assert f"- Closed issues: {summary['counts']['closed']}" in rendered
    assert "## In-Progress Issues" in rendered
    assert f"{issue_681_section}\n\n#681" in rendered
    assert "#681" in rendered
    assert "#681, #782" not in rendered
    assert "#681, #685" not in rendered
    assert "#756" not in rendered
    assert "## Fixed Locally Issues" in rendered
    assert "## Fixed Locally Issues\n\n_None._" in rendered
    assert "## PR-Open Issues" in rendered
    assert "## In-Progress Issues\n\n#681" in rendered
    assert "## PR-Open Issues\n\n#854" in rendered
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
        "#343, #344, #345, #375, #379, #380, #685, #686, #687, #691, #692, #693, #699, #814"
    ) in rendered
    assert "Current issues: #340, #782" not in rendered
    assert "Current issues: #673, #681, #683, #684, #854" in rendered
    assert "### `ai_attestation_and_model_governance`" in rendered
    assert "Current issues: _None._" in rendered
    assert "Current issues: #343, #344, #345, #375, #678, #693, #814" in rendered
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
