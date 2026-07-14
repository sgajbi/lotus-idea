from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

try:
    from scripts.persistence import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[import-not-found,no-redef]  # noqa: F401

from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.domain.proof_evidence import CIExecutionReceipt, ci_execution_receipt_from_mapping
from scripts.proof_generator_io import write_json_payload


ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_durable_repository_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            source_commit_sha=args.source_commit_sha,
            ci_execution_receipt=_load_receipt(args.ci_execution_receipt),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
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


def _load_receipt(path: str | None) -> CIExecutionReceipt | None:
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--ci-execution-receipt must contain a JSON object")
    receipt = ci_execution_receipt_from_mapping(payload)
    if receipt is None:
        raise ValueError("--ci-execution-receipt failed contract validation")
    return receipt


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
