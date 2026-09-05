from __future__ import annotations

from dataclasses import dataclass


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
