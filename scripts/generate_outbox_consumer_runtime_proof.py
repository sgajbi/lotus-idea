from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

from app.application.outbox_consumer_runtime_proof import (
    build_outbox_consumer_runtime_proof_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_outbox_consumer_runtime_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
        )
    except ValueError as exc:
        print(f"outbox consumer runtime proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0 if payload["outboxConsumerRuntimeProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe lotus-idea downstream consumer runtime proof artifact."
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
