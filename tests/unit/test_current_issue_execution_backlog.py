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
        if issue["issueNumber"] in {1154, 1155, 1156, 1162}
    }


def _assert_instruction_contains(issue: dict[str, Any], *fragments: str) -> None:
    instruction = cast(str, issue["closureInstruction"])
    assert [fragment for fragment in fragments if fragment not in instruction] == []


def test_execution_backlog_tracks_economic_candidate_identity() -> None:
    issue = _current_issues()[1154]

    assert issue["githubState"] == "closed"
    assert issue["executionStatus"] == "closed_complete"
    assert issue["allowPullRequestAutoClose"] is True
    assert issue["rfcSlices"] == ["slice-03", "slice-05", "slice-06", "slice-07"]
    _assert_instruction_contains(
        issue,
        "Closed #1154",
        "PR #1157",
        "Main Releasability run 33305344556",
        "CodeQL run 33305341663",
        "lotus-idea.wiki commit 189632a",
        "Branch cleanup",
        "businessIdentityId",
        "source content hashes as evidence lineage",
        "migration 016",
        "PostgreSQL concurrency proof",
        "removes caller duplicateOfCandidateId authority",
        "foundation_only with zero promoted features",
    )


def test_execution_backlog_tracks_product_quality_work() -> None:
    issues = _current_issues()
    feedback_quality = issues[1155]
    effectiveness = issues[1156]
    golden_evaluation = issues[1162]

    assert feedback_quality["executionStatus"] == "open_merged_main_qa_pending"
    assert feedback_quality["rfcSlices"] == ["slice-08", "slice-16", "slice-17"]
    _assert_instruction_contains(
        feedback_quality,
        "idea-feedback-taxonomy-v1",
        "source-safe offline evaluation projection",
        "status/merged-main pending canonical consumer QA",
        "no automatic policy",
        "sgajbi/lotus-workbench#953",
    )

    assert effectiveness["executionStatus"] == "open_merged_main_qa_pending"
    assert effectiveness["rfcSlices"] == ["slice-08", "slice-12", "slice-15", "slice-17"]
    _assert_instruction_contains(
        effectiveness,
        "opportunity-effectiveness-v1",
        "candidate-presentation-receipt-v1",
        "status/merged-main pending canonical consumer QA",
        "sgajbi/lotus-workbench#954",
        "presentation proxy",
    )

    assert golden_evaluation["githubState"] == "closed"
    assert golden_evaluation["executionStatus"] == "closed_complete"
    assert golden_evaluation["allowPullRequestAutoClose"] is True
    assert golden_evaluation["rfcSlices"] == [
        "slice-05",
        "slice-07",
        "slice-16",
        "slice-17",
    ]
    _assert_instruction_contains(
        golden_evaluation,
        "PR #1163",
        "f3aa9f1ddc76181d8e642cbba3712114be09254c",
        "Main Releasability run 33322378418",
        "CodeQL run 33322371179",
        "independently authored opportunity-quality golden evaluation set",
        "all 11 governed opportunity families",
        "all 12 implemented signal policies",
        "no-opportunity portfolio",
        "Expected outputs are handwritten",
        "5,732 unit tests",
        "PR #1164",
        "Main Releasability run 33323617114",
        "CodeQL run 33323616468",
        "ghcr.io/sgajbi/lotus-idea@sha256:d7701bbaa0411219659e6e0b4af04a434fe1a0d02f2a8eded665f48436e9935e",
        "lotus-idea.wiki commit 384c618",
        "strict DiffCount 0 parity",
        "does not create a compatibility layer",
    )
