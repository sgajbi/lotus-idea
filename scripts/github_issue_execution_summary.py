from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.github_issue_execution_ledger_gate import (  # noqa: E402
    LEDGER_PATH,
    IssueEntry,
    _entries,
    _load_json,
    validate_github_issue_execution_ledger,
)
from scripts.github_issue_learning_pattern_gate import (  # noqa: E402
    PATTERN_LEDGER_PATH,
    validate_github_issue_learning_patterns,
)


def build_issue_execution_summary(
    *,
    ledger_path: Path = LEDGER_PATH,
    pattern_path: Path = PATTERN_LEDGER_PATH,
) -> dict[str, Any]:
    validation_errors = [
        *validate_github_issue_execution_ledger(ledger_path),
        *validate_github_issue_learning_patterns(pattern_path),
    ]
    if validation_errors:
        raise ValueError("\n".join(validation_errors))

    ledger_payload = _load_json(ledger_path)
    entries = _entries(ledger_payload)
    pattern_payload = _load_json(pattern_path)

    return {
        "schemaVersion": "lotus-idea:rfc0002-github-issue-execution-summary:v1",
        "rfcId": ledger_payload["rfcId"],
        "repository": ledger_payload["repository"],
        "asOfDate": ledger_payload["asOfDate"],
        "sourceOfTruth": {
            "executionLedger": _repo_relative(ledger_path),
            "issueLearningPatterns": _repo_relative(pattern_path),
            "liveGitHubAudit": "make rfc0002-github-issue-execution-state-audit",
        },
        "counts": _counts(entries),
        "issuesByStatus": _issues_by_status(entries),
        "issuesBySlice": _issues_by_slice(entries),
        "learningPatterns": _learning_patterns(pattern_payload),
        "usageBoundary": (
            "This is source-controlled execution posture. Run the live GitHub state audit "
            "before quoting issue counts as current GitHub truth."
        ),
    }


def _counts(entries: Sequence[IssueEntry]) -> dict[str, Any]:
    by_github_state = Counter(entry.github_state for entry in entries)
    by_execution_status = Counter(entry.execution_status for entry in entries)
    open_count = by_github_state["open"]
    closed_count = by_github_state["closed"]
    return {
        "total": len(entries),
        "open": open_count,
        "closed": closed_count,
        "byGithubState": dict(sorted(by_github_state.items())),
        "byExecutionStatus": dict(sorted(by_execution_status.items())),
    }


def _issues_by_status(entries: Sequence[IssueEntry]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for entry in entries:
        grouped[entry.execution_status].append(entry.issue_number)
    return {status: sorted(issue_numbers) for status, issue_numbers in sorted(grouped.items())}


def _issues_by_slice(entries: Sequence[IssueEntry]) -> dict[str, list[int]]:
    grouped: dict[str, set[int]] = defaultdict(set)
    for entry in entries:
        for slice_id in entry.rfc_slices:
            grouped[slice_id].add(entry.issue_number)
    return {slice_id: sorted(issue_numbers) for slice_id, issue_numbers in sorted(grouped.items())}


def _learning_patterns(pattern_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_patterns = pattern_payload["patterns"]
    if not isinstance(raw_patterns, list):
        raise ValueError("patterns must be a list")
    patterns: list[dict[str, Any]] = []
    for raw_pattern in raw_patterns:
        if not isinstance(raw_pattern, Mapping):
            raise ValueError("pattern entries must be objects")
        current_issues = raw_pattern["currentLedgerIssueNumbers"]
        if not isinstance(current_issues, list):
            raise ValueError("currentLedgerIssueNumbers must be a list")
        patterns.append(
            {
                "patternId": raw_pattern["patternId"],
                "title": raw_pattern["title"],
                "currentOpenOrPendingIssues": sorted(current_issues),
                "futureAgentRule": raw_pattern["futureAgentRule"],
            }
        )
    return patterns


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def render_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary["counts"]
    status_counts = counts["byExecutionStatus"]
    lines = [
        f"# {summary['rfcId']} GitHub Issue Execution Summary",
        "",
        f"- Repository: `{summary['repository']}`",
        f"- Ledger as-of date: `{summary['asOfDate']}`",
        f"- Total tracked issues: {counts['total']}",
        f"- Open issues: {counts['open']}",
        f"- Closed issues: {counts['closed']}",
        "- Execution status counts:",
    ]
    lines.extend(f"  - `{status}`: {count}" for status, count in sorted(status_counts.items()))
    lines.extend(["", "## In-Progress Issues", ""])
    in_progress = summary["issuesByStatus"].get("open_in_progress", [])
    lines.append(_issue_list(in_progress))
    lines.extend(["", "## Fixed Locally Issues", ""])
    fixed_local = summary["issuesByStatus"].get("open_fixed_local", [])
    lines.append(_issue_list(fixed_local))
    lines.extend(["", "## PR-Open Issues", ""])
    lines.append(_issue_list(summary["issuesByStatus"].get("open_pr_raised", [])))
    lines.extend(["", "## Ready Issues", ""])
    lines.append(_issue_list(summary["issuesByStatus"].get("open_ready", [])))
    lines.extend(["", "## Blocked Issues", ""])
    lines.append(_issue_list(summary["issuesByStatus"].get("open_blocked", [])))
    lines.extend(["", "## Tracker Issues", ""])
    lines.append(_issue_list(summary["issuesByStatus"].get("open_tracker", [])))
    lines.extend(["", "## Learning Patterns", ""])
    for pattern in summary["learningPatterns"]:
        issue_numbers = _issue_list(pattern["currentOpenOrPendingIssues"])
        lines.extend(
            [
                f"### `{pattern['patternId']}`",
                "",
                pattern["title"],
                "",
                f"Current issues: {issue_numbers}",
                "",
                f"Future-agent rule: {pattern['futureAgentRule']}",
                "",
            ]
        )
    lines.extend(["## Usage Boundary", "", str(summary["usageBoundary"])])
    return "\n".join(lines).rstrip() + "\n"


def _issue_list(issue_numbers: Sequence[int]) -> str:
    if not issue_numbers:
        return "_None._"
    return ", ".join(f"#{issue_number}" for issue_number in issue_numbers)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize RFC-0002 issue execution posture from source-controlled ledgers."
    )
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--patterns", type=Path, default=PATTERN_LEDGER_PATH)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = build_issue_execution_summary(
            ledger_path=args.ledger,
            pattern_path=args.patterns,
        )
        rendered = (
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
            if args.format == "json"
            else render_markdown(summary)
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
