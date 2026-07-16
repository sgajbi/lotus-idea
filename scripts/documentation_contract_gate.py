from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from documentation import evidence_classification_inventory as evidence_inventory
    from documentation import implementation_proof_artifact_registry as artifact_registry
    from documentation.quality_contract import (
        code_fence_count,
        has_heading,
        markdown_table_count,
        mermaid_fence_count,
        non_empty_lines,
    )
    from documentation_stale_claims import PROHIBITED_STALE_CLAIMS, PROOF_READINESS_HEADINGS
    from wiki_navigation_contract import same_wiki_page_link_errors
except ModuleNotFoundError:
    from scripts.documentation import evidence_classification_inventory as evidence_inventory
    from scripts.documentation import implementation_proof_artifact_registry as artifact_registry
    from scripts.documentation.quality_contract import (
        code_fence_count,
        has_heading,
        markdown_table_count,
        mermaid_fence_count,
        non_empty_lines,
    )
    from scripts.documentation_stale_claims import (
        PROHIBITED_STALE_CLAIMS,
        PROOF_READINESS_HEADINGS,
    )
    from scripts.wiki_navigation_contract import same_wiki_page_link_errors


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DocumentationSurface:
    relative_path: str
    min_non_empty_lines: int
    required_fragments: tuple[str, ...]
    max_non_empty_lines: int | None = None


@dataclass(frozen=True)
class PolishedDocumentationSurface:
    relative_path: str
    required_headings: tuple[str, ...]
    min_markdown_tables: int
    min_code_fences: int
    min_mermaid_fences: int = 0


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
        260,
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
        "docs/demo/README.md",
        55,
        (
            "Client Understanding Flow",
            "Client-Friendly Message",
            "Client Pack Rules",
            "Required Validation",
            "Do Not Claim",
        ),
    ),
    DocumentationSurface(
        "docs/demo/client-demo-operating-process.md",
        60,
        (
            "Current Client-Demo Posture",
            "Client Demo Pack Template",
            "Claim Classification",
            "Client-Ready Acceptance",
            "Do Not Claim",
        ),
    ),
    DocumentationSurface(
        "docs/demo/client-facing-lotus-idea-brief.md",
        65,
        (
            "What Lotus Is Doing",
            "Client Problem",
            "What The Client Can See Today",
            "Why It Is Trustworthy",
            "How To Talk About It",
            "Evidence To Include In A Demo Pack",
        ),
    ),
    DocumentationSurface(
        "docs/demo/client-demo-pack.template.md",
        70,
        (
            "One-Page Client Brief",
            "Story Flow",
            "Claim Ledger",
            "Do-Not-Claim List",
            "Client-Ready Acceptance",
            "Follow-Up Register",
        ),
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
        "docs/research/advisor-intelligence-product-differentiation.md",
        70,
        (
            "not implementation or supported-feature evidence",
            "Differentiation Hypotheses",
            "Bank-Buyability Controls",
            "Research-To-Delivery Gate",
            "`lotus-ai`",
        ),
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
        ("Start Here", "Boundary", "Validation and CI"),
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
        "wiki/Validation-and-CI.md",
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
        "wiki/Security-and-Governance.md",
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
        40,
        ("Current posture", "Client Demo Flow", "Do Not Claim"),
    ),
    DocumentationSurface(
        "wiki/Roadmap.md",
        10,
        ("Roadmap", "Planned"),
    ),
)

POLISHED_SURFACES = (
    PolishedDocumentationSurface(
        "README.md",
        (
            "## Current Posture",
            "## Product Boundary",
            "## Architecture At A Glance",
            "## Validation And CI Lanes",
            "## Documentation Map",
        ),
        1,
        4,
        2,
    ),
    PolishedDocumentationSurface(
        "docs/operations/observability.md",
        (
            "## Default Signals",
            "## Sensitive-Content Rule",
            "## Idea Operation Events",
            "## Operator Interpretation",
        ),
        3,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/runbooks/service-operations.md",
        (
            "## Standard Commands",
            "## Health and Readiness",
            "## Incident First Checks",
        ),
        1,
        0,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/operations/implementation-proof-readiness.md",
        PROOF_READINESS_HEADINGS,
        2,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/operations/downstream-realization-readiness.md",
        PROOF_READINESS_HEADINGS,
        2,
        1,
    ),
    PolishedDocumentationSurface(
        "wiki/Overview.md",
        ("## Current posture",),
        1,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "wiki/Architecture.md",
        (
            "## Source Authority",
            "## Data Mesh Baseline",
            "## Certified API Foundation",
        ),
        1,
        2,
        2,
    ),
    PolishedDocumentationSurface(
        "wiki/Operations-Runbook.md",
        (
            "## Operator Map",
            "## Current Operation Event Diagnostics",
            "## API Certification Reference",
        ),
        1,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "wiki/Validation-and-CI.md",
        ("## Gate Map",),
        1,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "wiki/Demo-Readiness.md",
        (
            "## Current posture",
            "## Client Demo Flow",
            "## Client-Friendly Explanation",
            "## Claim States",
            "## Acceptance Checklist",
        ),
        3,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/demo/README.md",
        (
            "## Client Understanding Flow",
            "## Start Here",
            "## Client-Friendly Message",
            "## Client Pack Rules",
            "## Required Validation",
            "## Do Not Claim",
        ),
        3,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/demo/client-demo-operating-process.md",
        (
            "## Current Client-Demo Posture",
            "## Demo Story",
            "## Client-Friendly Explanation",
            "## Claim Classification",
            "## Client-Ready Acceptance",
            "## Do Not Claim",
        ),
        4,
        1,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/demo/client-facing-lotus-idea-brief.md",
        (
            "## What Lotus Is Doing",
            "## Client Problem",
            "## What The Client Can See Today",
            "## Why It Is Trustworthy",
            "## How To Talk About It",
            "## Evidence To Include In A Demo Pack",
        ),
        4,
        0,
        1,
    ),
    PolishedDocumentationSurface(
        "docs/demo/client-demo-pack.template.md",
        (
            "## Demo Control Summary",
            "## One-Page Client Brief",
            "## Story Flow",
            "## Demonstration Sequence",
            "## Claim Ledger",
            "## Client-Ready Acceptance",
            "## Follow-Up Register",
        ),
        5,
        2,
        1,
    ),
)

PROHIBITED_PLACEHOLDERS = ("TODO", "TBD", "lorem ipsum", "coming soon")


def validate_documentation_contract(
    *,
    root: Path = ROOT,
    surfaces: tuple[DocumentationSurface, ...] = REQUIRED_SURFACES,
    polished_surfaces: tuple[PolishedDocumentationSurface, ...] = POLISHED_SURFACES,
) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        path = root / surface.relative_path
        if not path.exists():
            errors.append(f"{surface.relative_path}: required documentation surface is missing")
            continue
        content = path.read_text(encoding="utf-8")
        non_empty_count = len(non_empty_lines(content))
        if non_empty_count < surface.min_non_empty_lines:
            errors.append(
                f"{surface.relative_path}: has {non_empty_count} non-empty lines; "
                f"minimum is {surface.min_non_empty_lines}"
            )
        if (
            surface.max_non_empty_lines is not None
            and non_empty_count > surface.max_non_empty_lines
        ):
            errors.append(
                f"{surface.relative_path}: has {non_empty_count} non-empty lines; "
                f"maximum is {surface.max_non_empty_lines}"
            )
        for fragment in surface.required_fragments:
            if fragment not in content:
                errors.append(f"{surface.relative_path}: missing required fragment `{fragment}`")
        for name in PROHIBITED_PLACEHOLDERS:
            if re.search(rf"\b{re.escape(name)}\b", content, re.IGNORECASE):
                errors.append(f"{surface.relative_path}: contains placeholder text `{name}`")
        for relative_path, stale_fragments, message in PROHIBITED_STALE_CLAIMS:
            if surface.relative_path == relative_path and any(
                fragment in content for fragment in stale_fragments
            ):
                errors.append(f"{surface.relative_path}: {message}")
    for surface in polished_surfaces:
        path = root / surface.relative_path
        if not path.exists():
            errors.append(f"{surface.relative_path}: polished documentation surface is missing")
            continue
        content = path.read_text(encoding="utf-8")
        for heading in surface.required_headings:
            if not has_heading(content, heading):
                errors.append(f"{surface.relative_path}: missing polished heading `{heading}`")
        table_count = markdown_table_count(content)
        if table_count < surface.min_markdown_tables:
            errors.append(
                f"{surface.relative_path}: has {table_count} markdown tables; "
                f"minimum is {surface.min_markdown_tables}"
            )
        fence_count = code_fence_count(content)
        if fence_count < surface.min_code_fences:
            errors.append(
                f"{surface.relative_path}: has {fence_count} code fences; "
                f"minimum is {surface.min_code_fences}"
            )
        mermaid_count = mermaid_fence_count(content)
        if mermaid_count < surface.min_mermaid_fences:
            errors.append(
                f"{surface.relative_path}: has {mermaid_count} Mermaid diagrams; "
                f"minimum is {surface.min_mermaid_fences}"
            )
    errors.extend(same_wiki_page_link_errors(root=root))
    errors.extend(evidence_inventory.evidence_classification_inventory_errors(root=root))
    errors.extend(artifact_registry.implementation_proof_artifact_registry_errors(root=root))
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
