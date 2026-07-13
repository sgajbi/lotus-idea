from __future__ import annotations


def non_empty_lines(content: str) -> list[str]:
    return [line for line in content.splitlines() if line.strip()]


def markdown_table_count(content: str) -> int:
    lines = content.splitlines()
    table_count = 0
    for index, line in enumerate(lines[:-1]):
        if not line.strip().startswith("|"):
            continue
        separator = lines[index + 1].strip()
        if separator.startswith("|") and "---" in separator:
            table_count += 1
    return table_count


def code_fence_count(content: str) -> int:
    return content.count("```") // 2


def mermaid_fence_count(content: str) -> int:
    return content.count("```mermaid")


def has_heading(content: str, heading: str) -> bool:
    return content.startswith(f"{heading}\n") or f"\n{heading}\n" in content
