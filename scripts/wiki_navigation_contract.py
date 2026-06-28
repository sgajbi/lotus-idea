from __future__ import annotations

import re
from pathlib import Path


MARKDOWN_LINK_TARGET = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def same_wiki_page_link_errors(*, root: Path) -> list[str]:
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return []

    errors: list[str] = []
    for path in sorted(wiki_root.glob("*.md")):
        for match in MARKDOWN_LINK_TARGET.finditer(path.read_text(encoding="utf-8")):
            target = _same_wiki_markdown_target(match.group(1))
            if target and (wiki_root / target).exists():
                errors.append(
                    f"{path.relative_to(root).as_posix()}: same-wiki link `{target}` "
                    "must omit `.md` for GitHub wiki navigation"
                )
    return errors


def _same_wiki_markdown_target(raw_target: str) -> str | None:
    target = raw_target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
    if "/" in target or "\\" in target or not target.endswith(".md"):
        return None
    return target
