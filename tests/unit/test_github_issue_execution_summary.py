from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
STATUS_SECTION_TITLES = {
    "open_in_progress": "## In-Progress Issues",
    "open_fixed_local": "## Fixed Locally Issues",
    "open_pr_raised": "## PR-Open Issues",
    "open_merged_main_qa_pending": "## Merged-Main QA Pending Issues",
    "open_ready": "## Ready Issues",
    "open_pending_final_closure": "## Pending Final Closure Issues",
    "open_pending_post_completion": "## Pending Post-Completion Issues",
    "open_blocked": "## Blocked Issues",
}


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


def _ledger_issues(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [issue for issue in payload["issues"] if isinstance(issue, dict)]


def _issue_numbers_by_status(
    ledger_issues: list[dict[str, Any]],
    execution_status: str,
) -> list[int]:
    return sorted(
        issue["issueNumber"]
        for issue in ledger_issues
        if issue["executionStatus"] == execution_status
    )


def _render_issue_numbers(issue_numbers: list[int]) -> str:
    if not issue_numbers:
        return "_None._"
    return ", ".join(f"#{issue_number}" for issue_number in issue_numbers)


def _assert_summary_status_bucket(
    summary: dict[str, Any],
    ledger_issues: list[dict[str, Any]],
    execution_status: str,
) -> None:
    expected_issue_numbers = _issue_numbers_by_status(ledger_issues, execution_status)
    if expected_issue_numbers:
        assert summary["issuesByStatus"][execution_status] == expected_issue_numbers
    else:
        assert execution_status not in summary["issuesByStatus"]


def _assert_rendered_status_section(
    rendered: str,
    ledger_issues: list[dict[str, Any]],
    execution_status: str,
) -> None:
    title = STATUS_SECTION_TITLES[execution_status]
    expected_rendering = _render_issue_numbers(
        _issue_numbers_by_status(ledger_issues, execution_status)
    )
    assert title in rendered
    assert f"{title}\n\n{expected_rendering}" in rendered


def _write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _live_github_states(
    module: ModuleType,
    ledger_payload: dict[str, Any],
) -> dict[int, Any]:
    status_label_by_execution_status = {
        "open_ready": "status/ready",
        "open_blocked": "status/blocked",
        "open_in_progress": "status/in-progress",
        "open_fixed_local": "status/fixed-local",
        "open_pr_raised": "status/pr-open",
        "open_merged_main_qa_pending": "status/merged-main",
        "open_tracker": "status/tracker",
        "open_pending_final_closure": "status/blocked",
        "open_pending_post_completion": "status/blocked",
        "closed_complete": "status/merged-main",
    }
    states: dict[int, Any] = {}
    for issue in _ledger_issues(ledger_payload):
        states[issue["issueNumber"]] = module.GitHubIssueState(
            issue_number=issue["issueNumber"],
            state=issue["githubState"].upper(),
            labels=frozenset(
                {
                    "rfc/RFC-0002",
                    *(f"rfc/RFC-0002/{slice_id}" for slice_id in issue["rfcSlices"]),
                    status_label_by_execution_status[issue["executionStatus"]],
                }
            ),
            title=f"Issue {issue['issueNumber']}",
            url=issue["url"],
        )

    states[379] = _state_with(states[379], status_label="status/in-progress")
    states[675] = _state_with(states[675], state="CLOSED", status_label="status/merged-main")
    states[1155] = _state_with(states[1155], state="CLOSED", status_label="status/merged-main")
    states[1222] = module.GitHubIssueState(
        issue_number=1222,
        state="OPEN",
        labels=frozenset({"rfc/RFC-0002", "rfc/RFC-0002/slice-09", "status/blocked"}),
        title="Governed idea-candidate explanation",
        url="https://github.com/sgajbi/lotus-idea/issues/1222",
    )
    states[1248] = module.GitHubIssueState(
        issue_number=1248,
        state="OPEN",
        labels=frozenset({"rfc/RFC-0002", "rfc/RFC-0002/slice-18", "status/in-progress"}),
        title="Derive execution posture from live GitHub state",
        url="https://github.com/sgajbi/lotus-idea/issues/1248",
    )
    return states


def _state_with(
    issue: Any,
    *,
    state: str | None = None,
    status_label: str,
) -> Any:
    return type(issue)(
        issue_number=issue.issue_number,
        state=state or issue.state,
        labels=frozenset(
            {label for label in issue.labels if not label.startswith("status/")} | {status_label}
        ),
        title=issue.title,
        url=issue.url,
    )


def test_github_issue_execution_summary_reports_current_rfc0002_counts() -> None:
    module = _load_summary()
    ledger_payload = _load_ledger_payload()
    ledger_issues = _ledger_issues(ledger_payload)
    github_issues = _live_github_states(module, ledger_payload)

    summary = module.build_issue_execution_summary(github_issues=github_issues)

    assert summary["schemaVersion"] == "lotus-idea:rfc0002-github-issue-execution-summary:v2"
    assert summary["counts"]["total"] == len(github_issues)
    assert 379 in summary["issuesByStatus"]["open_in_progress"]
    assert 1248 in summary["issuesByStatus"]["open_in_progress"]
    assert 675 in summary["issuesByStatus"]["closed_complete"]
    assert 1155 in summary["issuesByStatus"]["closed_complete"]
    assert 1222 in summary["issuesByStatus"]["open_blocked"]
    assert 675 not in summary["issuesByStatus"]["open_tracker"]
    assert 1248 in summary["issuesBySlice"]["slice-18"]
    assert summary["recordedLedgerSnapshot"]["asOfDate"] == ledger_payload["asOfDate"]
    assert summary["recordedLedgerSnapshot"]["counts"]["total"] == len(ledger_issues)
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
    github_issues = _live_github_states(module, ledger_payload)

    summary = module.build_issue_execution_summary(github_issues=github_issues)
    rendered = module.render_markdown(summary)
    ai_attestation_pattern = next(
        pattern
        for pattern in summary["learningPatterns"]
        if pattern["patternId"] == "ai_attestation_and_model_governance"
    )
    ai_attestation_current_issues = ai_attestation_pattern["currentOpenOrPendingIssues"]
    ai_attestation_current_rendering = (
        ", ".join(f"#{issue_number}" for issue_number in ai_attestation_current_issues)
        if ai_attestation_current_issues
        else "_None._"
    )

    assert "# RFC-0002 GitHub Issue Execution Summary" in rendered
    assert f"- Open issues: {summary['counts']['open']}" in rendered
    assert f"- Closed issues: {summary['counts']['closed']}" in rendered
    assert "## In-Progress Issues" in rendered
    assert "#681" in rendered
    assert "#379" in rendered
    assert "#1248" in rendered
    assert "## In-Progress Issues\n\n#379, #681, #685, #686, #1142, #1248" in rendered
    assert "## Pending Final Closure Issues\n\n_None._" in rendered
    assert "## Pending Post-Completion Issues\n\n_None._" in rendered
    assert "## Blocked Issues" in rendered
    assert "#343, #344, #345, #375, #380" in rendered
    assert "#1222" in rendered
    assert (
        "#675"
        not in rendered.split("## Tracker Issues", maxsplit=1)[1].split(
            "## Learning Patterns", maxsplit=1
        )[0]
    )
    assert "### `ai_attestation_and_model_governance`" in rendered
    assert f"Current issues: {ai_attestation_current_rendering}" in rendered
    assert ai_attestation_current_issues == []
    assert "_None._" in rendered
    assert (
        "Current counts, lifecycle status and issue lists are derived from live GitHub" in rendered
    )
    assert "GitHub is authoritative for current RFC-0002 execution state" in rendered
    assert "keep the source snapshot within its explicit age tolerance" not in rendered


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


def test_github_issue_execution_summary_reports_live_fetch_failure(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    module = _load_summary()

    def fail_live_fetch(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("GitHub unavailable")

    monkeypatch.setattr(module, "build_issue_execution_summary", fail_live_fetch)

    assert module.main([]) == 1
    assert capsys.readouterr().out == "GitHub unavailable\n"
