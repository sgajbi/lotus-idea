from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "architecture" / "GITHUB-ISSUE-CLOSURE-MATRIX.md"

ACTIONABLE_ISSUES = frozenset(
    {
        301,
        302,
        303,
        306,
        307,
        308,
        309,
        310,
        311,
        312,
        313,
        314,
        315,
        316,
        317,
        318,
        319,
        320,
        326,
        327,
        328,
        329,
        330,
        331,
        333,
        335,
        336,
        337,
    }
)

REQUIRED_COLUMNS = (
    "Issue",
    "Status",
    "Implementation Evidence",
    "Test And Gate Evidence",
    "Same-Pattern Scan",
    "Docs/Wiki/Context",
    "PR Close Intent",
)

ISSUE_RE = re.compile(r"#(?P<number>\d+)")
PATH_PREFIXES = (
    "src/",
    "scripts/",
    "tests/",
    "docs/",
    "wiki/",
    "contracts/",
    "supported-features/",
    "quality/",
)
ROOT_CONTEXT_FILES = (
    "AGENTS.md",
    "README.md",
    "REPOSITORY-ENGINEERING-CONTEXT.md",
    "Makefile",
)


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells)


def _matrix_rows(content: str) -> list[dict[str, str]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        headers = _split_row(line)
        if headers != list(REQUIRED_COLUMNS):
            continue
        if index + 1 >= len(lines) or not _is_separator(_split_row(lines[index + 1])):
            return []
        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.startswith("|"):
                break
            cells = _split_row(row_line)
            if len(cells) != len(headers):
                continue
            rows.append(dict(zip(headers, cells, strict=True)))
        return rows
    return []


def _issue_number(value: str) -> int | None:
    match = ISSUE_RE.search(value)
    if match is None:
        return None
    return int(match.group("number"))


def _has_path_or_command(value: str) -> bool:
    return (
        any(prefix in value for prefix in PATH_PREFIXES)
        or any(path in value for path in ROOT_CONTEXT_FILES)
        or "`make " in value
        or "`.dockerignore`" in value
    )


def validate_issue_closure_matrix(path: Path = MATRIX_PATH) -> list[str]:
    if not path.exists():
        return [f"{path.relative_to(ROOT).as_posix()}: required issue closure matrix is missing"]

    content = path.read_text(encoding="utf-8")
    rows = _matrix_rows(content)
    if not rows:
        return [
            f"{path.relative_to(ROOT).as_posix()}: missing required actionable issue matrix table"
        ]

    errors: list[str] = []
    seen_issues: set[int] = set()
    for row in rows:
        number = _issue_number(row["Issue"])
        if number is None:
            errors.append(f"{row['Issue']}: issue cell must include a GitHub issue number")
            continue
        if number in seen_issues:
            errors.append(f"#{number}: duplicate issue row")
        seen_issues.add(number)

        if number not in ACTIONABLE_ISSUES:
            errors.append(f"#{number}: issue is not in the current actionable closure set")
        if row["Status"] != "`locally_fixed`":
            errors.append(f"#{number}: status must be `locally_fixed` before PR creation")
        if not _has_path_or_command(row["Implementation Evidence"]):
            errors.append(f"#{number}: implementation evidence must cite code or contract paths")
        if not (
            "tests/" in row["Test And Gate Evidence"] or "`make " in row["Test And Gate Evidence"]
        ):
            errors.append(f"#{number}: test and gate evidence must cite tests or make targets")
        if "same-pattern" not in row["Same-Pattern Scan"].lower():
            errors.append(f"#{number}: same-pattern scan evidence is required")
        if not _has_path_or_command(row["Docs/Wiki/Context"]):
            errors.append(f"#{number}: docs/wiki/context evidence or decision is required")
        if f"Closes #{number}" not in row["PR Close Intent"]:
            errors.append(f"#{number}: PR close intent must contain `Closes #{number}`")

    missing = sorted(ACTIONABLE_ISSUES - seen_issues)
    extra = sorted(seen_issues - ACTIONABLE_ISSUES)
    if missing:
        errors.append(f"Missing actionable issue rows: {', '.join(f'#{n}' for n in missing)}")
    if extra:
        errors.append(f"Unexpected actionable issue rows: {', '.join(f'#{n}' for n in extra)}")
    return errors


def main() -> int:
    errors = validate_issue_closure_matrix()
    if errors:
        print("\n".join(errors))
        return 1
    print("GitHub issue closure matrix gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
