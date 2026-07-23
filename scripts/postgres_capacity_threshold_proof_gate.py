# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.postgres_capacity_threshold_proof import (
    validate_postgres_capacity_threshold_proof,
)


def validate_artifact(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PostgreSQL capacity threshold proof must be a JSON object")
    errors = validate_postgres_capacity_threshold_proof(payload)
    if errors:
        raise ValueError("; ".join(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Lotus Idea PostgreSQL capacity threshold proof artifact"
    )
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        validate_artifact(args.artifact)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PostgreSQL capacity threshold proof gate failed: {exc}", file=sys.stderr)
        return 1
    print("PostgreSQL capacity threshold proof gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
