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
        332,
        333,
        334,
        335,
        336,
        337,
        338,
        339,
        341,
        342,
        343,
        344,
        346,
        357,
        363,
        364,
        372,
        381,
        382,
        385,
        386,
        389,
        392,
        396,
        402,
        408,
        411,
        412,
        414,
        419,
        422,
        424,
        428,
        431,
        434,
        437,
        438,
        443,
        444,
        449,
        452,
        456,
        459,
        462,
        465,
        466,
        469,
        473,
        476,
        479,
        482,
        485,
        488,
        489,
        492,
        495,
        496,
        499,
        500,
        507,
        508,
        513,
        516,
        520,
        523,
        526,
        529,
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
ALLOWED_STATUSES = frozenset({"`locally_fixed`", "`partially_fixed`", "`merged_main`"})
MERGED_MAIN_ISSUES = frozenset(
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
        332,
        333,
        334,
        335,
        336,
        337,
        338,
        339,
        341,
        342,
        346,
        357,
        363,
        364,
        392,
        396,
        402,
        408,
        411,
        414,
        419,
        422,
        424,
        428,
        431,
        434,
        437,
        438,
        443,
        444,
        449,
        452,
        456,
        459,
        465,
        466,
        469,
        473,
        476,
        479,
        482,
        485,
        488,
        489,
        492,
        496,
        499,
        500,
        507,
        508,
        513,
        516,
        520,
        523,
        526,
        529,
    }
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
        status = row["Status"]
        if status not in ALLOWED_STATUSES:
            errors.append(
                f"#{number}: status must be `locally_fixed`, `partially_fixed`, or `merged_main`"
            )
        if number in MERGED_MAIN_ISSUES and status != "`merged_main`":
            errors.append(f"#{number}: merged-main issue cannot regress to {status}")
        if not _has_path_or_command(row["Implementation Evidence"]):
            errors.append(f"#{number}: implementation evidence must cite code or contract paths")
        if not (
            "tests/" in row["Test And Gate Evidence"]
            or "`make " in row["Test And Gate Evidence"]
            or " dispatch `" in row["Test And Gate Evidence"].lower()
        ):
            errors.append(
                f"#{number}: test and gate evidence must cite tests, make targets, "
                "or an executed workflow dispatch"
            )
        if "same-pattern" not in row["Same-Pattern Scan"].lower():
            errors.append(f"#{number}: same-pattern scan evidence is required")
        if not _has_path_or_command(row["Docs/Wiki/Context"]):
            errors.append(f"#{number}: docs/wiki/context evidence or decision is required")
        if status == "`locally_fixed`" and f"Closes #{number}" not in row["PR Close Intent"]:
            errors.append(f"#{number}: locally fixed intent must contain `Closes #{number}`")
        if status == "`partially_fixed`" and not any(
            phrase in row["PR Close Intent"]
            for phrase in (f"Keep #{number} open", f"Keeps #{number} open")
        ):
            errors.append(
                f"#{number}: partially fixed intent must contain `Keep #{number} open` "
                f"or `Keeps #{number} open`"
            )
        if status == "`merged_main`":
            test_evidence = row["Test And Gate Evidence"].lower()
            docs_evidence = row["Docs/Wiki/Context"].lower()
            close_evidence = row["PR Close Intent"].lower()
            if "main releasability" not in test_evidence or "codeql" not in test_evidence:
                errors.append(
                    f"#{number}: merged main evidence must cite Main Releasability and CodeQL"
                )
            if "wiki" not in docs_evidence or not any(
                phrase in docs_evidence for phrase in ("published", "publication")
            ):
                errors.append(f"#{number}: merged main evidence must cite wiki publication")
            if not all(term in close_evidence for term in ("closed", "main", "branch")):
                errors.append(
                    f"#{number}: merged main intent must record closed issue and branch cleanup"
                )

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
