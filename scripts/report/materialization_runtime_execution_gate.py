from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.report.materialization_runtime_execution import (  # noqa: E402
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
    report_materialization_runtime_execution_is_valid,
)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    path_value = args[0] if args else os.getenv(REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV)
    if not path_value:
        print(
            "Usage: materialization_runtime_execution_gate.py <proof-json-path> "
            f"or set {REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV}",
            file=sys.stderr,
        )
        return 2
    try:
        payload = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Report materialization runtime execution proof read error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print(
            "Report materialization runtime execution proof must be a JSON object", file=sys.stderr
        )
        return 1
    if not report_materialization_runtime_execution_is_valid(payload):
        print("Report materialization runtime execution proof is invalid", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
