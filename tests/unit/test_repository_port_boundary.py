from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = ROOT / "src" / "app" / "application"


def test_repository_protocols_are_owned_by_ports_layer() -> None:
    local_protocols: list[str] = []
    for path in APPLICATION_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith("Repository"):
                continue
            if any(_base_name(base) == "Protocol" for base in node.bases):
                local_protocols.append(f"{path.relative_to(ROOT)}:{node.name}")

    assert local_protocols == []


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return ""
