from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.ast_function_helpers import (
        is_non_implementation_stub as _is_non_implementation_stub,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from ast_function_helpers import (  # type: ignore[import-not-found,no-redef]
        is_non_implementation_stub as _is_non_implementation_stub,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCOPES = ("src/app", "scripts")
DEFAULT_MIN_FUNCTION_LINES = 6


@dataclass(frozen=True)
class FunctionRecord:
    path: str
    name: str
    line: int
    line_count: int
    fingerprint: str


def build_duplicate_inventory(
    root: Path = ROOT,
    *,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    min_function_lines: int = DEFAULT_MIN_FUNCTION_LINES,
) -> dict[str, Any]:
    records = _function_records(root, scopes=scopes, min_function_lines=min_function_lines)
    clusters_by_fingerprint: dict[str, list[FunctionRecord]] = {}
    for record in records:
        clusters_by_fingerprint.setdefault(record.fingerprint, []).append(record)

    clusters = [
        _cluster_payload(fingerprint, cluster_records)
        for fingerprint, cluster_records in sorted(clusters_by_fingerprint.items())
        if len(cluster_records) > 1
    ]
    clusters.sort(
        key=lambda cluster: (-cluster["count"], cluster["classification"], cluster["fingerprint"])
    )
    return {
        "schemaVersion": "lotus-idea.duplicate-implementation-inventory.v1",
        "mode": "report_only",
        "thresholdEnforced": False,
        "scopes": list(scopes),
        "minFunctionLines": min_function_lines,
        "functionCount": len(records),
        "duplicateClusterCount": len(clusters),
        "clusters": clusters,
    }


def validate_duplicate_inventory(
    root: Path = ROOT,
    *,
    fail_on_duplicates: bool = False,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    min_function_lines: int = DEFAULT_MIN_FUNCTION_LINES,
) -> list[str]:
    inventory = build_duplicate_inventory(
        root,
        scopes=scopes,
        min_function_lines=min_function_lines,
    )
    if not fail_on_duplicates:
        return []
    return [
        (
            "duplicate implementation cluster "
            f"{cluster['classification']} has {cluster['count']} exact function bodies"
        )
        for cluster in inventory["clusters"]
    ]


def _function_records(
    root: Path,
    *,
    scopes: tuple[str, ...],
    min_function_lines: int,
) -> list[FunctionRecord]:
    records: list[FunctionRecord] = []
    for scope in scopes:
        scope_root = root / scope
        if not scope_root.exists():
            continue
        for path in sorted(scope_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                end_line = getattr(node, "end_lineno", node.lineno)
                line_count = end_line - node.lineno + 1
                if line_count < min_function_lines:
                    continue
                if _is_non_implementation_stub(node):
                    continue
                records.append(
                    FunctionRecord(
                        path=path.relative_to(root).as_posix(),
                        name=node.name,
                        line=node.lineno,
                        line_count=line_count,
                        fingerprint=_fingerprint_function_body(node),
                    )
                )
    return records


def _fingerprint_function_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized_body = ast.Module(body=node.body, type_ignores=[])
    payload = ast.dump(
        normalized_body,
        annotate_fields=True,
        include_attributes=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cluster_payload(fingerprint: str, records: list[FunctionRecord]) -> dict[str, Any]:
    function_names = sorted({record.name for record in records})
    return {
        "fingerprint": fingerprint,
        "classification": _classify_cluster(function_names),
        "count": len(records),
        "functionNames": function_names,
        "locations": [asdict(record) for record in sorted(records, key=lambda item: item.path)],
    }


def _classify_cluster(function_names: list[str]) -> str:
    names = set(function_names)
    if names == {"_validate_forbidden_content"}:
        return "known_proof_source_safety_content_validation"
    if names <= {"_is_timezone_aware_datetime_text", "is_timezone_aware_datetime_text"}:
        return "known_proof_timezone_aware_datetime_text"
    return "unclassified_exact_function_body"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report exact duplicate first-party function bodies without writing artifacts."
    )
    parser.add_argument(
        "--fail-on-duplicates",
        action="store_true",
        help="Return non-zero when duplicate function bodies are present.",
    )
    parser.add_argument(
        "--min-function-lines",
        type=int,
        default=DEFAULT_MIN_FUNCTION_LINES,
        help="Minimum function length included in the inventory.",
    )
    args = parser.parse_args(argv)

    inventory = build_duplicate_inventory(min_function_lines=args.min_function_lines)
    print(json.dumps(inventory, indent=2, sort_keys=True))
    errors = validate_duplicate_inventory(
        fail_on_duplicates=args.fail_on_duplicates,
        min_function_lines=args.min_function_lines,
    )
    if errors:
        print("Duplicate implementation inventory failed:")
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
