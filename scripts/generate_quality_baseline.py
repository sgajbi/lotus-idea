from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "src", ROOT / "tests", ROOT / "scripts")
REPORT_PATH = ROOT / "quality" / "baseline_report.json"
MARKDOWN_PATH = ROOT / "quality" / "baseline_report.md"
ARCHITECTURE_REPORT_PATH = ROOT / "quality" / "architecture_boundary_report.json"


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        if root.exists():
            files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def _function_rows(path: Path) -> list[dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "name": node.name,
                    "line": node.lineno,
                    "lines": end_line - node.lineno + 1,
                }
            )
    return rows


def build_report() -> dict[str, object]:
    files = _python_files()
    functions = [row for path in files for row in _function_rows(path)]
    architecture_report_exists = ARCHITECTURE_REPORT_PATH.exists()
    architecture_report_status = "missing"
    if architecture_report_exists:
        try:
            architecture_payload = json.loads(ARCHITECTURE_REPORT_PATH.read_text(encoding="utf-8"))
            architecture_report_status = str(architecture_payload.get("status", "unknown"))
        except json.JSONDecodeError:
            architecture_report_status = "malformed"
    largest_files = sorted(
        (
            {
                "path": str(path.relative_to(ROOT)),
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
        "notes": [
            "Report-only scaffold baseline. Do not promote noisy metrics before baseline and exception policy are clear.",
            "OpenAPI, endpoint certification, supported-features, and no-sensitive-content gates remain separate deterministic scaffold checks.",
        ],
    }


def main() -> None:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    MARKDOWN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not report["architecture_boundary_report_exists"]:
        print(
            "WARNING: quality/architecture_boundary_report.json is missing; run make architecture-boundary-report."
        )
    print(f"Wrote {REPORT_PATH} and {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
