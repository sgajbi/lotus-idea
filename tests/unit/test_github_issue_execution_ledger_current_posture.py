import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = (
    ROOT / "contracts" / "implementation-proof" / "rfc0002-github-issue-execution-ledger.v1.json"
)


def _issue_by_number(issue_number: int) -> dict[str, Any]:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return next(issue for issue in payload["issues"] if issue["issueNumber"] == issue_number)


@pytest.mark.parametrize("issue_number", [1155, 1156])
def test_merged_idea_truth_remains_open_for_canonical_consumer_qa(issue_number: int) -> None:
    issue = _issue_by_number(issue_number)

    assert issue["githubState"] == "open"
    assert issue["executionStatus"] == "open_merged_main_qa_pending"
    assert issue["allowPullRequestAutoClose"] is False
    assert "status/merged-main pending canonical consumer QA" in issue["closureInstruction"]
    assert "Remaining completion evidence is consumer-owned" in issue["closureInstruction"]


@pytest.mark.parametrize(
    ("issue_number", "evidence_fragments"),
    [
        (
            1168,
            (
                "PR #1171",
                "cdc9fbc0cd64a0dec3fffe7fb42be384a394f0df",
                "Main Releasability run 33333214234",
                "CodeQL run 33333206828",
            ),
        ),
        (
            1169,
            (
                "PR #1173",
                "b923165ba1925eb59cbd3e74c9315c4f3659f7e7",
                "Main Releasability run 33353245168",
                "CodeQL run 33353237457",
            ),
        ),
        (
            1170,
            (
                "PR #1175",
                "df26f7f18c1dafb0009f8294cf08b999d1681ca0",
                "Main Releasability run 33360310207",
                "CodeQL run 33360303951",
            ),
        ),
    ],
)
def test_latest_exact_main_closures_are_durable(
    issue_number: int,
    evidence_fragments: tuple[str, ...],
) -> None:
    issue = _issue_by_number(issue_number)

    assert issue["githubState"] == "closed"
    assert issue["executionStatus"] == "closed_complete"
    assert issue["allowPullRequestAutoClose"] is True
    assert f"Closed #{issue_number} after QA passed" in issue["closureInstruction"]
    for evidence_fragment in evidence_fragments:
        assert evidence_fragment in issue["closureInstruction"]
    assert "No final RFC-0002 closure is claimed" in issue["closureInstruction"]
