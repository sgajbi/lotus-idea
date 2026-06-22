from __future__ import annotations

import ast
import sys
from pathlib import Path

MONETARY_HINTS = (
    "amount",
    "balance",
    "cash",
    "cost",
    "currency",
    "fx",
    "market",
    "money",
    "mtm",
    "nav",
    "notional",
    "pnl",
    "price",
    "rate",
    "value",
    "valuation",
)
ALLOWLIST = set()


def likely_monetary(value: str) -> bool:
    low = value.lower()
    return any(token in low for token in MONETARY_HINTS)


def _annotation_contains_float(annotation: ast.AST | None) -> bool:
    if annotation is None:
        return False
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id == "float":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "float":
            return True
    return False


def _target_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, ast.Attribute):
        return (target.attr,)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return tuple(names)
    return ()


def _is_float_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float"
    )


def _line(lines: list[str], lineno: int) -> str:
    if lineno < 1 or lineno > len(lines):
        return ""
    return lines[lineno - 1]


def _violation(path: Path, node: ast.AST, reason: str) -> str:
    return f"{path.as_posix()}:{node.lineno}: {reason}"


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _enclosing_function_name(parents: dict[ast.AST, ast.AST], node: ast.AST) -> str:
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return parent.name
        parent = parents.get(parent)
    return ""


def validate_monetary_float_usage(root: Path = Path(".")) -> list[str]:
    violations: list[str] = []
    source_root = root / "src"
    for path in sorted(source_root.rglob("*.py")):
        relative_path = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text, filename=str(path))
        parents = _parent_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _annotation_contains_float(node.returns) and likely_monetary(node.name):
                    violation = _violation(
                        relative_path,
                        node,
                        "monetary float return annotation detected",
                    )
                    if violation not in ALLOWLIST:
                        violations.append(violation)
            elif isinstance(node, ast.AnnAssign):
                target_names = _target_names(node.target)
                if _annotation_contains_float(node.annotation) and any(
                    likely_monetary(name) for name in target_names
                ):
                    violation = _violation(
                        relative_path,
                        node,
                        "monetary float annotation detected",
                    )
                    if violation not in ALLOWLIST:
                        violations.append(violation)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, float):
                    if any(likely_monetary(name) for name in target_names):
                        violation = _violation(
                            relative_path,
                            node,
                            "monetary float literal detected",
                        )
                        if violation not in ALLOWLIST:
                            violations.append(violation)
            elif isinstance(node, ast.Assign):
                target_names = tuple(
                    name for target in node.targets for name in _target_names(target)
                )
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, float):
                    if any(likely_monetary(name) for name in target_names):
                        violation = _violation(
                            relative_path,
                            node,
                            "monetary float literal detected",
                        )
                        if violation not in ALLOWLIST:
                            violations.append(violation)
                if _is_float_call(node.value) and any(
                    likely_monetary(name) for name in target_names
                ):
                    violation = _violation(
                        relative_path,
                        node,
                        "monetary float conversion detected",
                    )
                    if violation not in ALLOWLIST:
                        violations.append(violation)
            elif isinstance(node, ast.arg):
                if _annotation_contains_float(node.annotation) and likely_monetary(node.arg):
                    violation = _violation(
                        relative_path,
                        node,
                        "monetary float parameter annotation detected",
                    )
                    if violation not in ALLOWLIST:
                        violations.append(violation)
            elif _is_float_call(node) and (
                likely_monetary(_line(lines, node.lineno))
                or likely_monetary(_enclosing_function_name(parents, node))
            ):
                violation = _violation(
                    relative_path,
                    node,
                    "monetary float conversion detected",
                )
                if violation not in ALLOWLIST:
                    violations.append(violation)
    return sorted(set(violations))


def main() -> int:
    violations = validate_monetary_float_usage()
    if violations:
        print("\n".join(violations))
        return 1
    print("Monetary float guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
