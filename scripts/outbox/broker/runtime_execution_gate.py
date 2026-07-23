# ruff: noqa: E402
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.broker.runtime_execution import (  # noqa: E402
    OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
    outbox_broker_runtime_execution_is_valid,
)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    path_value = args[0] if args else os.getenv(OUTBOX_BROKER_RUNTIME_EXECUTION_ENV)
    if not path_value:
        print(
            "Usage: runtime_execution_gate.py <proof-json-path> "
            f"or set {OUTBOX_BROKER_RUNTIME_EXECUTION_ENV}",
            file=sys.stderr,
        )
        return 2
    try:
        payload = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Outbox broker runtime execution proof read error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("Outbox broker runtime execution proof must be a JSON object", file=sys.stderr)
        return 1
    if not outbox_broker_runtime_execution_is_valid(payload):
        print("Outbox broker runtime execution proof is invalid", file=sys.stderr)
        return 1
    print("Outbox broker runtime execution proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
