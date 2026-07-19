# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
import sys

try:
    from scripts.outbox._bootstrap import ROOT
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from _bootstrap import ROOT  # type: ignore[import-not-found,no-redef]

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.consumer_contract_proof import (  # noqa: E402
    build_outbox_consumer_contract_proof_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_outbox_consumer_contract_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
        )
    except ValueError as exc:
        print(f"outbox consumer contract proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0 if payload["outboxConsumerContractProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe lotus-idea downstream consumer contract proof artifact."
        )
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
