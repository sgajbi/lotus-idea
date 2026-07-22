from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = (
    ROOT / "contracts" / "implementation-proof" / "rfc0002-github-issue-execution-ledger.v1.json"
)

EXPECTED_SCHEMA_VERSION = "lotus-idea:rfc0002-github-issue-execution-ledger:v1"
EXPECTED_RFC_ID = "RFC-0002"
EXPECTED_REPOSITORY = "sgajbi/lotus-idea"
EXPECTED_EXECUTION_ISSUES = frozenset(
    {
        340,
        343,
        344,
        345,
        375,
        379,
        380,
        482,
        542,
        673,
        674,
        675,
        676,
        677,
        678,
        679,
        680,
        681,
        682,
        683,
        684,
        685,
        686,
        687,
        688,
        689,
        690,
        691,
        692,
        693,
        694,
        695,
        696,
        697,
        698,
        699,
        700,
        701,
        702,
        704,
    }
)
OPEN_STATUSES = frozenset(
    {
        "open_tracker",
        "open_blocked",
        "open_in_progress",
        "open_fixed_local",
        "open_pr_raised",
        "open_merged_main_qa_pending",
        "open_pending_final_closure",
        "open_pending_post_completion",
    }
)
CLOSED_STATUSES = frozenset({"closed_complete"})
AUTO_CLOSE_KEYWORDS = (
    "close",
    "closes",
    "closed",
    "fix",
    "fixes",
    "fixed",
    "resolve",
    "resolves",
    "resolved",
)


@dataclass(frozen=True)
class IssueEntry:
    issue_number: int
    github_state: str
    execution_status: str
    allow_pull_request_auto_close: bool
    closure_instruction: str
    rfc_slices: tuple[str, ...]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(ROOT).as_posix()} is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(ROOT).as_posix()} must contain a JSON object")
    return payload


def _entries(payload: dict[str, Any]) -> list[IssueEntry]:
    raw_issues = payload.get("issues")
    if not isinstance(raw_issues, list):
        raise ValueError("issues must be a list")

    entries: list[IssueEntry] = []
    for index, raw_entry in enumerate(raw_issues):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"issues[{index}] must be an object")
        issue_number = raw_entry.get("issueNumber")
        github_state = raw_entry.get("githubState")
        execution_status = raw_entry.get("executionStatus")
        allow_pull_request_auto_close = raw_entry.get("allowPullRequestAutoClose")
        closure_instruction = raw_entry.get("closureInstruction")
        rfc_slices = raw_entry.get("rfcSlices")
        if not isinstance(issue_number, int):
            raise ValueError(f"issues[{index}].issueNumber must be an integer")
        if github_state not in {"open", "closed"}:
            raise ValueError(f"#{issue_number}: githubState must be open or closed")
        if not isinstance(execution_status, str):
            raise ValueError(f"#{issue_number}: executionStatus must be a string")
        if not isinstance(allow_pull_request_auto_close, bool):
            raise ValueError(f"#{issue_number}: allowPullRequestAutoClose must be boolean")
        if not isinstance(closure_instruction, str) or not closure_instruction.strip():
            raise ValueError(f"#{issue_number}: closureInstruction is required")
        if not isinstance(rfc_slices, list) or not rfc_slices:
            raise ValueError(f"#{issue_number}: rfcSlices must be a non-empty list")
        if not all(isinstance(slice_id, str) for slice_id in rfc_slices):
            raise ValueError(f"#{issue_number}: every rfcSlices entry must be a string")

        entries.append(
            IssueEntry(
                issue_number=issue_number,
                github_state=github_state,
                execution_status=execution_status,
                allow_pull_request_auto_close=allow_pull_request_auto_close,
                closure_instruction=closure_instruction,
                rfc_slices=tuple(rfc_slices),
            )
        )
    return entries


def _auto_close_phrase_re(issue_number: int) -> re.Pattern[str]:
    keywords = "|".join(re.escape(keyword) for keyword in AUTO_CLOSE_KEYWORDS)
    return re.compile(rf"\b(?:{keywords})\s+#{issue_number}\b", re.IGNORECASE)


def validate_github_issue_execution_ledger(path: Path = LEDGER_PATH) -> list[str]:
    try:
        payload = _load_json(path)
        entries = _entries(payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    if payload.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        errors.append("schemaVersion must be lotus-idea:rfc0002-github-issue-execution-ledger:v1")
    if payload.get("rfcId") != EXPECTED_RFC_ID:
        errors.append("rfcId must be RFC-0002")
    if payload.get("repository") != EXPECTED_REPOSITORY:
        errors.append("repository must be sgajbi/lotus-idea")

    seen: set[int] = set()
    for entry in entries:
        number = entry.issue_number
        if number in seen:
            errors.append(f"#{number}: duplicate issue entry")
        seen.add(number)
        if number not in EXPECTED_EXECUTION_ISSUES:
            errors.append(f"#{number}: issue is not in the RFC-0002 execution issue set")

        if entry.github_state == "open":
            if entry.execution_status not in OPEN_STATUSES:
                errors.append(f"#{number}: open issue has invalid executionStatus")
            if entry.allow_pull_request_auto_close:
                errors.append(f"#{number}: open issue cannot allow PR auto-close")
            if f"Keep #{number} open" not in entry.closure_instruction:
                errors.append(
                    f"#{number}: open issue closureInstruction must contain Keep #{number} open"
                )
            if _auto_close_phrase_re(number).search(entry.closure_instruction):
                errors.append(
                    f"#{number}: open issue closureInstruction must not contain GitHub "
                    "auto-close wording"
                )
        else:
            if entry.execution_status not in CLOSED_STATUSES:
                errors.append(f"#{number}: closed issue has invalid executionStatus")
            if not entry.allow_pull_request_auto_close:
                errors.append(f"#{number}: closed issue must allow historical PR auto-close")
            if f"Closed #{number}" not in entry.closure_instruction:
                errors.append(
                    f"#{number}: closed issue closureInstruction must contain Closed #{number}"
                )

    missing = sorted(EXPECTED_EXECUTION_ISSUES - seen)
    extra = sorted(seen - EXPECTED_EXECUTION_ISSUES)
    if missing:
        errors.append(
            f"Missing RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in missing)}"
        )
    if extra:
        errors.append(
            f"Unexpected RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in extra)}"
        )
    return errors


def main() -> int:
    errors = validate_github_issue_execution_ledger()
    if errors:
        print("\n".join(errors))
        return 1
    print("RFC-0002 GitHub issue execution ledger gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
