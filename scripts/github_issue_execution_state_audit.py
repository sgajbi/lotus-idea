# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.github_issue_execution_ledger_gate import (
    CLOSED_STATUSES,
    EXPECTED_EXECUTION_ISSUES,
    LEDGER_PATH,
    OPEN_STATUSES,
    IssueEntry,
    _entries,
    _load_json,
)


EXPECTED_OPEN_LABEL_BY_STATUS = {
    "open_blocked": "status/blocked",
    "open_in_progress": "status/in-progress",
    "open_merged_main_qa_pending": "status/merged-main",
}
EXPECTED_CLOSED_LABEL = "status/merged-main"
EXPECTED_RFC_LABEL = "rfc/RFC-0002"
GITHUB_ISSUE_FIELDS = "number,state,title,labels,url"


@dataclass(frozen=True)
class GitHubIssueState:
    issue_number: int
    state: str
    labels: frozenset[str]
    title: str
    url: str


def load_github_issue_states(path: Path) -> dict[int, GitHubIssueState]:
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list):
        raise ValueError("GitHub issue state input must be a JSON list")
    return _parse_github_issue_states(raw_payload)


def fetch_github_issue_states(*, repository: str, limit: int) -> dict[int, GitHubIssueState]:
    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repository,
            "--state",
            "all",
            "--limit",
            str(limit),
            "--json",
            GITHUB_ISSUE_FIELDS,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"gh issue list failed: {stderr}")
    raw_payload = json.loads(result.stdout)
    if not isinstance(raw_payload, list):
        raise ValueError("gh issue list returned non-list JSON")
    return _parse_github_issue_states(raw_payload)


def audit_github_issue_execution_state(
    *,
    ledger_path: Path = LEDGER_PATH,
    github_issues: Mapping[int, GitHubIssueState],
) -> list[str]:
    try:
        ledger_payload = _load_json(ledger_path)
        ledger_entries = _entries(ledger_payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    seen_ledger_issues = {entry.issue_number for entry in ledger_entries}
    missing_expected = sorted(EXPECTED_EXECUTION_ISSUES - seen_ledger_issues)
    if missing_expected:
        errors.append(
            "ledger is missing expected RFC-0002 issue entries: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_expected)
        )

    for entry in ledger_entries:
        github_issue = github_issues.get(entry.issue_number)
        if github_issue is None:
            errors.append(f"#{entry.issue_number}: missing from GitHub issue state")
            continue
        errors.extend(_audit_issue_state(entry, github_issue))

    tracked_github_issues = set(github_issues)
    missing_from_github_input = sorted(seen_ledger_issues - tracked_github_issues)
    if missing_from_github_input:
        errors.append(
            "GitHub state input omitted ledger issues: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_from_github_input)
        )

    errors.extend(_audit_rfc_label_coverage(ledger_entries, github_issues))
    return errors


def _audit_issue_state(entry: IssueEntry, github_issue: GitHubIssueState) -> list[str]:
    errors: list[str] = []
    expected_github_state = entry.github_state.upper()
    if github_issue.state != expected_github_state:
        errors.append(
            f"#{entry.issue_number}: ledger githubState={entry.github_state} "
            f"but GitHub state={github_issue.state.lower()}"
        )

    if entry.github_state == "open" and entry.execution_status not in OPEN_STATUSES:
        errors.append(f"#{entry.issue_number}: open ledger entry has invalid execution status")
    if entry.github_state == "closed" and entry.execution_status not in CLOSED_STATUSES:
        errors.append(f"#{entry.issue_number}: closed ledger entry has invalid execution status")

    expected_label = EXPECTED_OPEN_LABEL_BY_STATUS.get(entry.execution_status)
    if expected_label is not None and expected_label not in github_issue.labels:
        errors.append(
            f"#{entry.issue_number}: executionStatus={entry.execution_status} "
            f"requires GitHub label {expected_label}"
        )
    if (
        entry.execution_status == "closed_complete"
        and EXPECTED_CLOSED_LABEL not in github_issue.labels
    ):
        errors.append(
            f"#{entry.issue_number}: closed_complete requires GitHub label {EXPECTED_CLOSED_LABEL}"
        )
    if entry.execution_status == "open_blocked" and github_issue.state != "OPEN":
        errors.append(f"#{entry.issue_number}: blocked execution issue must remain open")
    return errors


def _audit_rfc_label_coverage(
    ledger_entries: Sequence[IssueEntry],
    github_issues: Mapping[int, GitHubIssueState],
) -> list[str]:
    ledger_issue_numbers = {entry.issue_number for entry in ledger_entries}
    rfc_labeled_issue_numbers = {
        issue.issue_number for issue in github_issues.values() if EXPECTED_RFC_LABEL in issue.labels
    }
    errors: list[str] = []

    missing_from_ledger = sorted(rfc_labeled_issue_numbers - ledger_issue_numbers)
    if missing_from_ledger:
        errors.append(
            f"{EXPECTED_RFC_LABEL} GitHub issues missing from execution ledger: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_from_ledger)
        )

    missing_rfc_label = sorted(
        entry.issue_number
        for entry in ledger_entries
        if (github_issue := github_issues.get(entry.issue_number)) is not None
        and EXPECTED_RFC_LABEL not in github_issue.labels
    )
    if missing_rfc_label:
        errors.append(
            "ledger issues missing GitHub label "
            f"{EXPECTED_RFC_LABEL}: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_rfc_label)
        )
    return errors


def _parse_github_issue_states(
    payload: Sequence[Mapping[str, Any]],
) -> dict[int, GitHubIssueState]:
    states: dict[int, GitHubIssueState] = {}
    for index, raw_issue in enumerate(payload):
        issue_number = raw_issue.get("number")
        state = raw_issue.get("state")
        title = raw_issue.get("title")
        url = raw_issue.get("url")
        labels = raw_issue.get("labels")
        if not isinstance(issue_number, int):
            raise ValueError(f"GitHub issue state item {index} has non-integer number")
        if state not in {"OPEN", "CLOSED"}:
            raise ValueError(f"GitHub issue #{issue_number} has invalid state")
        if not isinstance(title, str):
            raise ValueError(f"GitHub issue #{issue_number} has invalid title")
        if not isinstance(url, str):
            raise ValueError(f"GitHub issue #{issue_number} has invalid url")
        if not isinstance(labels, list):
            raise ValueError(f"GitHub issue #{issue_number} has invalid labels")
        label_names = frozenset(_label_names(labels, issue_number=issue_number))
        states[issue_number] = GitHubIssueState(
            issue_number=issue_number,
            state=state,
            labels=label_names,
            title=title,
            url=url,
        )
    return states


def _label_names(labels: Sequence[object], *, issue_number: int) -> tuple[str, ...]:
    names: list[str] = []
    for index, raw_label in enumerate(labels):
        if not isinstance(raw_label, Mapping):
            raise ValueError(f"GitHub issue #{issue_number} label {index} is not an object")
        name = raw_label.get("name")
        if not isinstance(name, str):
            raise ValueError(f"GitHub issue #{issue_number} label {index} has invalid name")
        names.append(name)
    return tuple(names)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the RFC-0002 GitHub issue execution ledger against current GitHub issue state."
        )
    )
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument(
        "--github-issues-json",
        type=Path,
        help="Offline gh issue list JSON fixture. If omitted, the script calls gh.",
    )
    parser.add_argument("--repo", default="sgajbi/lotus-idea")
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        github_issues = (
            load_github_issue_states(args.github_issues_json)
            if args.github_issues_json is not None
            else fetch_github_issue_states(repository=args.repo, limit=args.limit)
        )
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    errors = audit_github_issue_execution_state(
        ledger_path=args.ledger,
        github_issues=github_issues,
    )
    if errors:
        print("\n".join(errors))
        return 1
    print("GitHub issue execution state audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
