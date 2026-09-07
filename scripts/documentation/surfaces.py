from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REQUIRED_REPOSITORY_CONTEXT_HEADINGS = (
    "## Repository Role",
    "## Business And Domain Responsibility",
    "## Current-State Summary",
    "## Architecture And Module Map",
    "## Runtime And Integration Boundaries",
    "## Repo-Native Commands",
    "## Validation And CI Expectations",
    "## Standards And RFCs That Govern This Repository",
    "## Known Constraints And Implementation Notes",
    "## Context Maintenance Rule",
    "## Cross-Links",
)


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
    max_mermaid_fences: int | None = None


PROGRESSIVE_CONTEXT_SURFACES = (
    DocumentationSurface(
        "REPOSITORY-ENGINEERING-CONTEXT.md",
        150,
        (
            "Current-State Summary",
            "Repo-Native Commands",
            "Validation And CI Expectations",
            "make documentation-contract-gate",
            "Context Maintenance Rule",
        ),
        350,
    ),
    DocumentationSurface(
        "CLAUDE.md",
        8,
        (
            "thin adapter, not a second policy source",
            "AGENTS.md",
            "REPOSITORY-ENGINEERING-CONTEXT.md",
            "LOTUS-SKILL-ROUTING-MAP.md",
            "Without it, use the canonical links above",
        ),
        24,
    ),
)


def repository_context_heading_errors(root: Path) -> list[str]:
    path = root / "REPOSITORY-ENGINEERING-CONTEXT.md"
    if not path.exists():
        return []
    headings = tuple(
        line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("## ")
    )
    if headings == REQUIRED_REPOSITORY_CONTEXT_HEADINGS:
        return []
    return [
        "REPOSITORY-ENGINEERING-CONTEXT.md: headings must match the progressive "
        "repository-context contract in order"
    ]
