# ruff: noqa: E402
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.consumer_runtime import (  # noqa: E402
    OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV,
    outbox_consumer_runtime_execution_is_valid,
)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    path_value = args[0] if args else os.getenv(OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV)
    if not path_value:
        print(
            "Usage: consumer_runtime_execution_gate.py <proof-json-path> "
            f"or set {OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV}",
            file=sys.stderr,
        )
        return 2
    try:
        payload = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Outbox consumer runtime execution proof read error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("Outbox consumer runtime execution proof must be a JSON object", file=sys.stderr)
        return 1
    if not outbox_consumer_runtime_execution_is_valid(payload):
        print("Outbox consumer runtime execution proof is invalid", file=sys.stderr)
        return 1
    print("Outbox consumer runtime execution proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
