from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


LEDGER_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "implementation-proof"
    / "rfc0002-github-issue-execution-ledger.v1.json"
)


def _current_issues() -> dict[int, dict[str, Any]]:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {
        cast(int, issue["issueNumber"]): issue
        for issue in payload["issues"]
        if issue["issueNumber"] in {1154, 1155, 1156}
    }


def _assert_instruction_contains(issue: dict[str, Any], *fragments: str) -> None:
    instruction = cast(str, issue["closureInstruction"])
    assert [fragment for fragment in fragments if fragment not in instruction] == []


def test_execution_backlog_tracks_economic_candidate_identity() -> None:
    issue = _current_issues()[1154]

    assert issue["githubState"] == "open"
    assert issue["executionStatus"] == "open_pr_raised"
    assert issue["allowPullRequestAutoClose"] is False
    assert issue["rfcSlices"] == ["slice-03", "slice-05", "slice-06", "slice-07"]
    _assert_instruction_contains(
        issue,
        "Keep #1154 open",
        "businessIdentityId",
        "source content hashes as evidence lineage",
        "migration 016",
        "PostgreSQL concurrency proof",
        "remove caller duplicateOfCandidateId authority",
        "foundation_only with zero promoted features",
    )


def test_execution_backlog_orders_feedback_quality_before_effectiveness() -> None:
    issues = _current_issues()
    feedback_quality = issues[1155]
    effectiveness = issues[1156]

    assert feedback_quality["executionStatus"] == "open_ready"
    assert feedback_quality["rfcSlices"] == ["slice-08", "slice-16", "slice-17"]
    _assert_instruction_contains(
        feedback_quality,
        "versioned adviser-feedback outcome/reason taxonomy",
        "tenant-scoped source-safe offline evaluation projection",
        "no automatic policy",
        "Workbench may consume the canonical taxonomy",
    )

    assert effectiveness["executionStatus"] == "open_ready"
    assert effectiveness["rfcSlices"] == ["slice-08", "slice-12", "slice-15", "slice-17"]
    _assert_instruction_contains(
        effectiveness,
        "opportunity-effectiveness read model",
        "Define every numerator, denominator, window",
        "bounded index-supported PostgreSQL aggregates",
        "low-cardinality",
    )
