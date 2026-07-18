from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "app"
REPORT_PATH = ROOT / "quality" / "architecture_boundary_report.json"
REPORT_SCHEMA_VERSION = "architecture-boundary-report.v2"

LAYER_RULES = {
    "domain": {
        "forbidden_prefixes": (
            "fastapi",
            "starlette",
            "pydantic",
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
        "forbidden_prefixes": ("app.infrastructure", "app.runtime"),
        "description": (
            "API routes should call application services and the API runtime dependency facade "
            "rather than concrete infrastructure or runtime composition modules."
        ),
    },
    "runtime": {
        "forbidden_prefixes": ("fastapi", "starlette", "app.api"),
        "description": "Runtime composition may wire concrete adapters but must not depend on HTTP routes, DTOs, or framework modules.",
    },
}

API_RUNTIME_DEPENDENCY_FACADE = SRC_ROOT / "api" / "runtime_dependencies.py"


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


def _source_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _json_compatible(payload: Any) -> Any:
    return json.loads(_canonical_json(payload))


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _source_import_inventory() -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "module": _module_name(path),
            "imports": sorted(_imports(path)),
        }
        for path in _source_files()
    ]


def _input_fingerprint() -> dict[str, object]:
    inventory = _source_import_inventory()
    return {
        "source_root": SRC_ROOT.relative_to(ROOT).as_posix(),
        "source_file_count": len(inventory),
        "source_import_digest": _digest(inventory),
        "rule_digest": _digest(LAYER_RULES),
    }


def _layer_for(path: Path) -> str | None:
    relative = path.relative_to(SRC_ROOT)
    return relative.parts[0] if relative.parts else None


def _is_allowed_layer_import(path: Path, layer: str, imported: str) -> bool:
    if layer == "api" and path == API_RUNTIME_DEPENDENCY_FACADE:
        return imported == "app.runtime" or imported.startswith("app.runtime.")
    return False


def validate_architecture_boundaries() -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in _source_files():
        layer = _layer_for(path)
        if layer not in LAYER_RULES:
            continue
        imports = _imports(path)
        for imported in sorted(imports):
            for prefix in LAYER_RULES[layer]["forbidden_prefixes"]:
                if _is_allowed_layer_import(path, layer, imported):
                    continue
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


def build_architecture_report(mode: str) -> dict[str, object]:
    violations = validate_architecture_boundaries()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "mode": mode,
        "status": "failed" if violations else "passed",
        "input_fingerprint": _input_fingerprint(),
        "violations": violations,
        "rules": _json_compatible(LAYER_RULES),
    }


def validate_architecture_report_freshness(
    report_path: Path | None = None,
) -> list[str]:
    report_path = report_path or REPORT_PATH
    relative_path = (
        report_path.relative_to(ROOT).as_posix()
        if report_path.is_relative_to(ROOT)
        else str(report_path)
    )
    if not report_path.exists():
        return [
            f"{relative_path}: missing committed architecture boundary report; "
            "run `make architecture-boundary-report`"
        ]
    try:
        current_report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            f"{relative_path}: malformed JSON ({exc.msg}); run `make architecture-boundary-report`"
        ]
    expected_report = build_architecture_report("report-only")
    errors: list[str] = []
    if current_report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append(
            f"{relative_path}: missing or unsupported schema_version; "
            "run `make architecture-boundary-report`"
        )
    if current_report.get("mode") != "report-only":
        errors.append(
            f"{relative_path}: committed report mode must be `report-only`; "
            "run `make architecture-boundary-report`"
        )
    if current_report.get("input_fingerprint") != expected_report["input_fingerprint"]:
        errors.append(
            f"{relative_path}: stale source/rule fingerprint; "
            "run `make architecture-boundary-report`"
        )
    for field in ("repository", "status", "violations", "rules"):
        if current_report.get(field) != expected_report[field]:
            errors.append(
                f"{relative_path}: stale `{field}` field; run `make architecture-boundary-report`"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("report-only", "blocking"),
        default="report-only",
    )
    args = parser.parse_args()
    report = build_architecture_report(args.mode)
    violations = cast(list[dict[str, str]], report["violations"])
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
    if args.mode == "blocking":
        freshness_errors = validate_architecture_report_freshness()
        if freshness_errors:
            print("Architecture boundary report freshness gate failed:")
            print(json.dumps(freshness_errors, indent=2, sort_keys=True))
            return 1
    label = "report" if args.mode == "report-only" else "gate"
    print(f"Architecture boundary {label} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
