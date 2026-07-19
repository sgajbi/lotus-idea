# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

try:
    from scripts.persistence import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[import-not-found,no-redef]  # noqa: F401


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.durable_repository_proof import build_durable_repository_proof_payload
from scripts.proof_generator_io import load_ci_execution_receipt, write_json_payload


ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_durable_repository_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            source_commit_sha=args.source_commit_sha,
            ci_execution_receipt=load_ci_execution_receipt(args.ci_execution_receipt),
        )
    except (OSError, ValueError) as exc:
        print(f"durable repository proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea durable PostgreSQL repository proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--source-commit-sha", required=True)
    parser.add_argument("--ci-execution-receipt")
    parser.add_argument("--output")
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
