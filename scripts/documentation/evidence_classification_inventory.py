from __future__ import annotations

import re
from pathlib import Path


EVIDENCE_CLASSIFICATION_INVENTORY_PATH = Path(
    "docs/architecture/implementation-proof-evidence-classification.md"
)
ISSUE_CLOSURE_MATRIX_PATH = Path("docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md")
_ISSUE_NUMBER_RE = re.compile(r"\[#(?P<number>\d+)\]")
_TRACKING_ISSUE_NUMBER_RE = re.compile(r"#(?P<number>\d+)")
_CAMPAIGN_OCCURRENCE_EXCLUSION = "campaign occurrence: no"
_COMPLETED_POSTURE_MARKERS = ("closed", "exact-main", "hardened", "implemented", "merged")
_STALE_COMPLETION_MARKERS = (
    "next separately bounded occurrence",
    "pending occurrence",
    "planned occurrence",
    "untrusted until replaced",
)


def _primary_tracking_issue_number(line: str) -> int | None:
    cells = line.split("|")
    if len(cells) < 4:
        return None
    match = _TRACKING_ISSUE_NUMBER_RE.search(cells[-2])
    return int(match.group("number")) if match is not None else None


def evidence_classification_inventory_errors(*, root: Path) -> list[str]:
    inventory_path = root / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_path = root / ISSUE_CLOSURE_MATRIX_PATH
    if not inventory_path.exists() or not matrix_path.exists():
        return []

    completed_occurrences: set[int] = set()
    merged_issue_rows: dict[int, str] = {}
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| [#") or "| `merged_main` |" not in line:
            continue
        match = _ISSUE_NUMBER_RE.search(line)
        if match is None:
            continue
        issue_number = int(match.group("number"))
        merged_issue_rows[issue_number] = line
        if "#393" not in line and "evidence-classification campaign" not in line:
            continue
        if _CAMPAIGN_OCCURRENCE_EXCLUSION in line.lower():
            continue
        completed_occurrences.add(issue_number)

    inventory = inventory_path.read_text(encoding="utf-8")
    inventory_rows = {
        issue_number: line
        for line in inventory.splitlines()
        if line.startswith("|")
        and (issue_number := _primary_tracking_issue_number(line)) is not None
    }
    missing = sorted(
        issue_number for issue_number in completed_occurrences if issue_number not in inventory_rows
    )
    inventory_label = EVIDENCE_CLASSIFICATION_INVENTORY_PATH.as_posix()
    errors: list[str] = []
    if missing:
        formatted = ", ".join(f"#{issue_number}" for issue_number in missing)
        errors.append(f"{inventory_label}: missing completed campaign occurrences: {formatted}")

    unregistered = sorted(
        issue_number
        for issue_number in set(inventory_rows) & set(merged_issue_rows)
        if issue_number not in completed_occurrences
        and _CAMPAIGN_OCCURRENCE_EXCLUSION not in merged_issue_rows[issue_number].lower()
    )
    if unregistered:
        formatted = ", ".join(f"#{issue_number}" for issue_number in unregistered)
        errors.append(
            f"{inventory_label}: completed inventory occurrences lack campaign registration: "
            f"{formatted}"
        )

    stale = sorted(
        issue_number
        for issue_number in completed_occurrences - set(missing)
        if not any(
            marker in inventory_rows[issue_number].lower() for marker in _COMPLETED_POSTURE_MARKERS
        )
        or any(
            marker in inventory_rows[issue_number].lower() for marker in _STALE_COMPLETION_MARKERS
        )
    )
    if stale:
        formatted = ", ".join(f"#{issue_number}" for issue_number in stale)
        errors.append(
            f"{inventory_label}: completed campaign occurrences retain pending posture: {formatted}"
        )
    return errors
