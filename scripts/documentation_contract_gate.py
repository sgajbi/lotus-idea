from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DocumentationSurface:
    relative_path: str
    min_non_empty_lines: int
    required_fragments: tuple[str, ...]


REQUIRED_SURFACES = (
    DocumentationSurface(
        "AGENTS.md",
        80,
        (
            "Mandatory Reading Order",
            "Wiki Publication Rule",
            "Context Maintenance Rule",
        ),
    ),
    DocumentationSurface(
        "README.md",
        150,
        (
            "Product Boundary",
            "Data Mesh Posture",
            "Quick Start",
            "make documentation-contract-gate",
            "LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md",
        ),
    ),
    DocumentationSurface(
        "REPOSITORY-ENGINEERING-CONTEXT.md",
        250,
        (
            "Current-State Summary",
            "Repo-Native Commands",
            "Validation And CI Expectations",
            "make documentation-contract-gate",
            "Context Maintenance Rule",
        ),
    ),
    DocumentationSurface(
        "docs/rfcs/README.md",
        25,
        ("RFC-0002 Slice Evidence Files", "RFC Rules"),
    ),
    DocumentationSurface(
        "docs/standards/enterprise-readiness.md",
        12,
        (
            "make documentation-contract-gate",
            "LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md",
        ),
    ),
    DocumentationSurface(
        "docs/runbooks/service-operations.md",
        25,
        ("Standard Commands", "Health and Readiness", "Incident First Checks"),
    ),
    DocumentationSurface(
        "docs/operations/api-certification.md",
        15,
        ("Certified Foundation Endpoints", "Source-Degraded And Reconciliation Endpoints"),
    ),
    DocumentationSurface(
        "docs/operations/mesh-readiness.md",
        40,
        ("Source Truth", "Promotion Rule", "Runtime Diagnostic", "Repo-Native Gate"),
    ),
    DocumentationSurface(
        "docs/operations/observability.md",
        25,
        ("Default Signals", "Sensitive-Content Rule", "Idea Operation Events"),
    ),
    DocumentationSurface(
        "quality/ci_quality_gates.md",
        25,
        ("make documentation-contract-gate", "implementation-truth-gate"),
    ),
    DocumentationSurface(
        "quality/quality_scorecard.md",
        10,
        ("Bank-Buyable Quality Scorecard", "Documentation and operations"),
    ),
    DocumentationSurface(
        "evidence/rfc-implementation/README.md",
        5,
        ("repository", "branch", "commit SHA", "validation command"),
    ),
    DocumentationSurface(
        "wiki/Home.md",
        15,
        ("Start Here", "Boundary", "Validation And CI"),
    ),
    DocumentationSurface(
        "wiki/Overview.md",
        10,
        ("Current posture", "opportunity intelligence"),
    ),
    DocumentationSurface(
        "wiki/Architecture.md",
        30,
        ("Source Authority", "Data Mesh Baseline", "Certified API Foundation"),
    ),
    DocumentationSurface(
        "wiki/Integrations.md",
        30,
        ("Upstream", "Downstream", "Data Product Dependencies"),
    ),
    DocumentationSurface(
        "wiki/Operations-Runbook.md",
        25,
        ("Current Operation Event Diagnostics", "API Certification Reference"),
    ),
    DocumentationSurface(
        "wiki/Validation-And-CI.md",
        40,
        ("make documentation-contract-gate", "Branch hygiene policy"),
    ),
    DocumentationSurface(
        "wiki/Development-Workflow.md",
        10,
        ("stranded-truth reconciliation", "make documentation-contract-gate"),
    ),
    DocumentationSurface(
        "wiki/Supported-Features.md",
        20,
        ("Current posture", "Promotion rule"),
    ),
    DocumentationSurface(
        "wiki/Security-And-Governance.md",
        15,
        ("Security", "Governance"),
    ),
    DocumentationSurface(
        "wiki/RFC-Index.md",
        15,
        ("RFC-0002", "Slice"),
    ),
    DocumentationSurface(
        "wiki/Demo-Readiness.md",
        10,
        ("Current posture", "not"),
    ),
    DocumentationSurface(
        "wiki/Roadmap.md",
        10,
        ("Roadmap", "Planned"),
    ),
)

PROHIBITED_PLACEHOLDERS = (
    ("TODO", re.compile(r"\bTODO\b", re.IGNORECASE)),
    ("TBD", re.compile(r"\bTBD\b", re.IGNORECASE)),
    ("lorem ipsum", re.compile(r"\blorem ipsum\b", re.IGNORECASE)),
    ("coming soon", re.compile(r"\bcoming soon\b", re.IGNORECASE)),
)


def _non_empty_lines(content: str) -> list[str]:
    return [line for line in content.splitlines() if line.strip()]


def validate_documentation_contract(
    *,
    root: Path = ROOT,
    surfaces: tuple[DocumentationSurface, ...] = REQUIRED_SURFACES,
) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        path = root / surface.relative_path
        if not path.exists():
            errors.append(f"{surface.relative_path}: required documentation surface is missing")
            continue
        content = path.read_text(encoding="utf-8")
        non_empty_count = len(_non_empty_lines(content))
        if non_empty_count < surface.min_non_empty_lines:
            errors.append(
                f"{surface.relative_path}: has {non_empty_count} non-empty lines; "
                f"minimum is {surface.min_non_empty_lines}"
            )
        for fragment in surface.required_fragments:
            if fragment not in content:
                errors.append(f"{surface.relative_path}: missing required fragment `{fragment}`")
        for name, pattern in PROHIBITED_PLACEHOLDERS:
            if pattern.search(content):
                errors.append(f"{surface.relative_path}: contains placeholder text `{name}`")
    return errors


def main() -> int:
    errors = validate_documentation_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Documentation contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
