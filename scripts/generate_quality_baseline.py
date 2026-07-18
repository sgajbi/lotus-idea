from __future__ import annotations

import ast
import json
from pathlib import Path

try:
    from architecture_boundary_gate import validate_architecture_report_freshness
except ImportError:  # pragma: no cover - supports package-style imports in tests/tools
    from scripts.architecture_boundary_gate import validate_architecture_report_freshness

try:
    from ast_function_helpers import (
        is_non_implementation_stub as _is_non_implementation_stub,
    )
except ImportError:  # pragma: no cover - supports package-style imports in tests/tools
    from scripts.ast_function_helpers import (  # type: ignore[import-not-found,no-redef]
        is_non_implementation_stub as _is_non_implementation_stub,
    )

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "quality" / "baseline_report.json"
MARKDOWN_PATH = ROOT / "quality" / "baseline_report.md"
ARCHITECTURE_REPORT_PATH = ROOT / "quality" / "architecture_boundary_report.json"


def _source_roots(root: Path) -> tuple[Path, ...]:
    return (root / "src", root / "tests", root / "scripts")


def _python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for source_root in _source_roots(root):
        if source_root.exists():
            files.extend(
                path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts
            )
    return sorted(files)


def _function_rows(path: Path, root: Path) -> list[dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_non_implementation_stub(node):
                continue
            end_line = getattr(node, "end_lineno", node.lineno)
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "name": node.name,
                    "line": node.lineno,
                    "lines": end_line - node.lineno + 1,
                }
            )
    return rows


def build_report(root: Path = ROOT) -> dict[str, object]:
    architecture_report_path = root / "quality" / "architecture_boundary_report.json"
    files = _python_files(root)
    functions = [row for path in files for row in _function_rows(path, root)]
    architecture_report_exists = architecture_report_path.exists()
    architecture_report_status = "missing"
    architecture_report_freshness_errors: list[str] = []
    if architecture_report_exists:
        try:
            architecture_payload = json.loads(architecture_report_path.read_text(encoding="utf-8"))
            architecture_report_status = str(architecture_payload.get("status", "unknown"))
        except json.JSONDecodeError:
            architecture_report_status = "malformed"
        architecture_report_freshness_errors = validate_architecture_report_freshness(
            architecture_report_path
        )
    largest_files = sorted(
        (
            {
                "path": path.relative_to(root).as_posix(),
                "lines": len(path.read_text(encoding="utf-8").splitlines()),
            }
            for path in files
        ),
        key=lambda item: int(item["lines"]),
        reverse=True,
    )[:10]
    largest_functions = sorted(
        functions,
        key=lambda item: int(item["lines"]),
        reverse=True,
    )[:10]
    return {
        "repository": "lotus-idea",
        "mode": "report-only",
        "service_profile": "domain-service",
        "python_files": len(files),
        "python_functions": len(functions),
        "largest_files": largest_files,
        "largest_functions": largest_functions,
        "architecture_boundary_report": "quality/architecture_boundary_report.json",
        "architecture_boundary_report_exists": architecture_report_exists,
        "architecture_boundary_report_status": architecture_report_status,
        "architecture_boundary_report_freshness_status": (
            "current"
            if architecture_report_exists and not architecture_report_freshness_errors
            else "stale"
        ),
        "architecture_boundary_report_freshness_errors": architecture_report_freshness_errors,
        "notes": [
            "Report-only scaffold baseline. Do not promote noisy metrics before baseline and exception policy are clear.",
            "OpenAPI, endpoint certification, supported-features, and no-sensitive-content gates remain separate deterministic scaffold checks.",
        ],
    }


def write_report(root: Path = ROOT) -> dict[str, object]:
    report_path = root / "quality" / "baseline_report.json"
    markdown_path = root / "quality" / "baseline_report.md"
    report = build_report(root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Quality Baseline",
        "",
        f"Repository: `{report['repository']}`",
        "",
        "Mode: `report-only`",
        "",
        f"Service profile: `{report['service_profile']}`",
        "",
        f"Python files: `{report['python_files']}`",
        f"Python functions: `{report['python_functions']}`",
        "",
        f"Architecture boundary report: `{report['architecture_boundary_report_status']}`",
        "Architecture boundary report freshness: "
        f"`{report['architecture_boundary_report_freshness_status']}`",
        "",
        "## Largest Files",
        "",
    ]
    lines.extend(f"- `{item['path']}`: {item['lines']} lines" for item in report["largest_files"])
    lines.extend(["", "## Largest Functions", ""])
    lines.extend(
        f"- `{item['path']}::{item['name']}`: {item['lines']} lines"
        for item in report["largest_functions"]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = write_report()
    if not report["architecture_boundary_report_exists"]:
        print(
            "WARNING: quality/architecture_boundary_report.json is missing; run make architecture-boundary-report."
        )
    print(f"Wrote {REPORT_PATH} and {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
