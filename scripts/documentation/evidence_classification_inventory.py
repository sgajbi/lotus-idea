from __future__ import annotations

import re
from pathlib import Path


EVIDENCE_CLASSIFICATION_INVENTORY_PATH = Path(
    "docs/architecture/implementation-proof-evidence-classification.md"
)
ISSUE_CLOSURE_MATRIX_PATH = Path("docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md")
_ISSUE_NUMBER_RE = re.compile(r"\[#(?P<number>\d+)\]")
_CAMPAIGN_OCCURRENCE_EXCLUSION = "campaign occurrence: no"


def evidence_classification_inventory_errors(*, root: Path) -> list[str]:
    inventory_path = root / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_path = root / ISSUE_CLOSURE_MATRIX_PATH
    if not inventory_path.exists() or not matrix_path.exists():
        return []

    completed_occurrences: set[int] = set()
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| [#") or "| `merged_main` |" not in line:
            continue
        if "#393" not in line and "evidence-classification campaign" not in line:
            continue
        if _CAMPAIGN_OCCURRENCE_EXCLUSION in line.lower():
            continue
        match = _ISSUE_NUMBER_RE.search(line)
        if match is not None:
            completed_occurrences.add(int(match.group("number")))

    inventory = inventory_path.read_text(encoding="utf-8")
    missing = sorted(
        issue_number
        for issue_number in completed_occurrences
        if f"#{issue_number}" not in inventory
    )
    if not missing:
        return []
    formatted = ", ".join(f"#{issue_number}" for issue_number in missing)
    inventory_label = EVIDENCE_CLASSIFICATION_INVENTORY_PATH.as_posix()
    return [f"{inventory_label}: missing completed campaign occurrences: {formatted}"]
