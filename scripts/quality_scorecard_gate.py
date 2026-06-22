from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORECARD_PATH = ROOT / "quality" / "quality_scorecard.md"

ALLOWED_STATUSES = {
    "Implemented",
    "Partially implemented",
    "Planned",
    "Not applicable",
    "Unknown - requires owner review",
}

REQUIRED_CONTROLS = (
    "Architecture",
    "API and contracts",
    "Data and methodology",
    "Security and privacy",
    "Observability and supportability",
    "Resilience and performance",
    "Testing",
    "CI and release evidence",
    "Documentation and operations",
)

REQUIRED_EVIDENCE_ANCHORS: dict[str, tuple[str, ...]] = {
    "Architecture": ("architecture-boundary-gate", "maintainability-gate"),
    "API and contracts": ("OpenAPI", "endpoint certification"),
    "Data and methodology": ("source", "high-cash"),
    "Security and privacy": ("No-sensitive-content", "caller context"),
    "Observability and supportability": ("operation", "health/readiness"),
    "Resilience and performance": ("PostgreSQL", "idempotency"),
    "Testing": ("Unit", "integration", "e2e"),
    "CI and release evidence": (
        "documentation contract",
        "implementation-truth",
        "PostgreSQL runtime proof",
    ),
    "Documentation and operations": ("README", "wiki", "documentation-contract-gate"),
}

STALE_SCORECARD_PATTERNS: dict[str, re.Pattern[str]] = {
    "business_endpoints_not_implemented": re.compile(
        r"\bBusiness endpoints not yet implemented\b",
        re.IGNORECASE,
    ),
    "business_behavior_tests_not_implemented": re.compile(
        r"\bBusiness behavior tests not yet implemented\b",
        re.IGNORECASE,
    ),
    "business_supportability_not_implemented": re.compile(
        r"\bBusiness supportability states not yet implemented\b",
        re.IGNORECASE,
    ),
    "domain_methodology_not_applicable": re.compile(
        r"\bDomain methodology not yet applicable\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class ScorecardRow:
    control_area: str
    status: str
    evidence: str
    gap: str
    next_slice: str


def _strip_markdown_code(value: str) -> str:
    return value.strip().strip("`").strip()


def _parse_scorecard_rows(content: str) -> list[ScorecardRow]:
    rows: list[ScorecardRow] = []
    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0] in {"Control Area", "---"}:
            continue
        if set(cells[0]) == {"-"}:
            continue
        rows.append(
            ScorecardRow(
                control_area=cells[0],
                status=_strip_markdown_code(cells[1]),
                evidence=cells[2],
                gap=cells[3],
                next_slice=cells[4],
            )
        )
    return rows


def validate_quality_scorecard(path: Path = SCORECARD_PATH) -> list[str]:
    if not path.exists():
        return [f"{path.relative_to(ROOT).as_posix()}: required quality scorecard is missing"]

    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for name, pattern in STALE_SCORECARD_PATTERNS.items():
        if pattern.search(content):
            errors.append(
                f"quality/quality_scorecard.md: stale scaffold-era scorecard claim `{name}`"
            )

    rows = _parse_scorecard_rows(content)
    row_by_control = {row.control_area: row for row in rows}

    for control in REQUIRED_CONTROLS:
        row = row_by_control.get(control)
        if row is None:
            errors.append(f"quality/quality_scorecard.md: missing control row `{control}`")
            continue
        if row.status not in ALLOWED_STATUSES:
            errors.append(
                f"quality/quality_scorecard.md: `{control}` has unsupported status `{row.status}`"
            )
        for field_name, value in (
            ("Evidence", row.evidence),
            ("Gap", row.gap),
            ("Next Slice", row.next_slice),
        ):
            if not value.strip():
                errors.append(
                    f"quality/quality_scorecard.md: `{control}` has empty `{field_name}` cell"
                )

        evidence_lower = row.evidence.lower()
        for anchor in REQUIRED_EVIDENCE_ANCHORS[control]:
            if anchor.lower() not in evidence_lower:
                errors.append(
                    f"quality/quality_scorecard.md: `{control}` evidence missing `{anchor}`"
                )

    unexpected_controls = sorted(set(row_by_control) - set(REQUIRED_CONTROLS))
    for control in unexpected_controls:
        errors.append(f"quality/quality_scorecard.md: unexpected control row `{control}`")

    return errors


def main() -> int:
    errors = validate_quality_scorecard()
    if errors:
        print("\n".join(errors))
        return 1
    print("Quality scorecard gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
