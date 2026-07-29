from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.github_issue_execution_ledger_gate import (  # noqa: E402
    AUTO_CLOSE_KEYWORDS,
    LEDGER_PATH,
    _entries,
    _load_json,
)

KEEP_OPEN_RE = re.compile(r"\bKeep\s+#(?P<number>\d+)\s+open\b", re.IGNORECASE)


def validate_pr_text(
    *,
    title: str,
    body: str,
    ledger_path: Path = LEDGER_PATH,
) -> list[str]:
    text = f"{title}\n\n{body}".strip()
    if not text:
        return []

    open_keep_issue_numbers = _open_keep_issue_numbers(ledger_path)
    referenced_keep_open_issues = _referenced_keep_open_issues(text, open_keep_issue_numbers)
    if not referenced_keep_open_issues:
        return []

    unsafe_keywords = _unsafe_auto_close_keywords(text)
    if not unsafe_keywords:
        return []

    issues = ", ".join(f"#{number}" for number in referenced_keep_open_issues)
    keywords = ", ".join(f"`{keyword}`" for keyword in unsafe_keywords)
    return [
        (
            "PR text references keep-open RFC-0002 issue(s) "
            f"{issues} but contains GitHub auto-close keyword(s) {keywords}. "
            "Use neutral verbs such as `updates`, `records`, `reconciles`, or `addresses`, "
            "and keep completion language out of partial PR titles and bodies."
        )
    ]


def _open_keep_issue_numbers(ledger_path: Path) -> frozenset[int]:
    payload = _load_json(ledger_path)
    return frozenset(
        entry.issue_number
        for entry in _entries(payload)
        if entry.github_state == "open" and not entry.allow_pull_request_auto_close
    )


def _referenced_keep_open_issues(text: str, open_issue_numbers: frozenset[int]) -> tuple[int, ...]:
    issue_numbers = {
        int(match.group("number"))
        for match in KEEP_OPEN_RE.finditer(text)
        if int(match.group("number")) in open_issue_numbers
    }
    return tuple(sorted(issue_numbers))


def _unsafe_auto_close_keywords(text: str) -> tuple[str, ...]:
    found: set[str] = set()
    for keyword in AUTO_CLOSE_KEYWORDS:
        pattern = re.compile(rf"(?<!auto-)\b{re.escape(keyword)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            if _is_safe_hyphenated_term(text, match.end()):
                continue
            if _is_safe_negated_boundary(text, match.start()):
                continue
            found.add(match.group(0).lower())
    return tuple(sorted(found))


def _is_safe_hyphenated_term(text: str, keyword_end: int) -> bool:
    suffix = text[keyword_end : keyword_end + 16].lower()
    return suffix.startswith("-forward")


def _is_safe_negated_boundary(text: str, keyword_start: int) -> bool:
    prefix = text[max(0, keyword_start - 32) : keyword_start].lower()
    safe_phrases = (
        "do not ",
        "does not ",
        "did not ",
        "not ",
        "no ",
        "without ",
    )
    return any(prefix.endswith(phrase) for phrase in safe_phrases)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prevent partial RFC-0002 PR text from mixing Keep-open issue references "
            "with GitHub auto-close wording."
        )
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--title-env")
    parser.add_argument("--body-env")
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    title = os.environ.get(args.title_env, "") if args.title_env else args.title
    body = os.environ.get(args.body_env, "") if args.body_env else args.body
    try:
        errors = validate_pr_text(title=title, body=body, ledger_path=args.ledger)
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 1
    if errors:
        print("\n".join(errors))
        return 1
    print("GitHub issue PR text gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
