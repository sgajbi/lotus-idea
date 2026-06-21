from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "app"
REPORT_PATH = ROOT / "quality" / "architecture_boundary_report.json"

LAYER_RULES = {
    "domain": {
        "forbidden_prefixes": (
            "fastapi",
            "starlette",
            "requests",
            "httpx",
            "sqlalchemy",
            "app.api",
            "app.infrastructure",
            "app.contracts",
        ),
        "description": "Domain must stay framework-free and independent from API, contract, and infrastructure modules.",
    },
    "application": {
        "forbidden_prefixes": ("fastapi", "starlette", "app.infrastructure", "app.api"),
        "description": "Application services may orchestrate domain and ports but must not depend on HTTP/framework or concrete infrastructure.",
    },
    "api": {
        "forbidden_prefixes": ("app.infrastructure",),
        "description": "API routes should call application services rather than concrete infrastructure.",
    },
}


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _layer_for(path: Path) -> str | None:
    relative = path.relative_to(SRC_ROOT)
    return relative.parts[0] if relative.parts else None


def validate_architecture_boundaries() -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in SRC_ROOT.rglob("*.py"):
        layer = _layer_for(path)
        if layer not in LAYER_RULES:
            continue
        imports = _imports(path)
        for imported in sorted(imports):
            for prefix in LAYER_RULES[layer]["forbidden_prefixes"]:
                if imported == prefix or imported.startswith(f"{prefix}."):
                    violations.append(
                        {
                            "path": str(path.relative_to(ROOT)),
                            "module": _module_name(path),
                            "layer": layer,
                            "import": imported,
                            "rule": LAYER_RULES[layer]["description"],
                        }
                    )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("report-only", "blocking"),
        default="report-only",
    )
    args = parser.parse_args()
    violations = validate_architecture_boundaries()
    report = {
        "repository": "lotus-idea",
        "mode": args.mode,
        "status": "failed" if violations else "passed",
        "violations": violations,
        "rules": LAYER_RULES,
    }
    if args.mode == "report-only":
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if violations:
        label = "report" if args.mode == "report-only" else "gate"
        print(f"Architecture boundary {label} found {len(violations)} violation(s).")
        if args.mode == "blocking":
            print(json.dumps(violations, indent=2, sort_keys=True))
            return 1
        return 0
    label = "report" if args.mode == "report-only" else "gate"
    print(f"Architecture boundary {label} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
