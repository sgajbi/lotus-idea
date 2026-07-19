# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys


from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.ai_runtime_proof import (
    build_unavailable_ai_workflow_pack_runtime_execution_proof_payload,
    execute_ai_workflow_pack_runtime_proof,
)
from app.infrastructure.lotus_ai import HttpLotusAIWorkflowRuntime

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _aware_datetime(args.generated_at_utc)
        payload = execute_ai_workflow_pack_runtime_proof(
            generated_at_utc=generated_at_utc,
            runtime=HttpLotusAIWorkflowRuntime(
                base_url=args.lotus_ai_base_url,
                timeout_seconds=args.timeout_seconds,
            ),
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"AI workflow-pack runtime execution proof error: {exc}", file=sys.stderr)
        if not args.allow_runtime_unavailable:
            return 2
        payload = build_unavailable_ai_workflow_pack_runtime_execution_proof_payload(
            generated_at_utc=generated_at_utc
        )

    write_json_payload(payload, output=args.output)
    if args.allow_runtime_unavailable and not payload["aiWorkflowPackRuntimeExecutionProofValid"]:
        return 0
    return 0 if payload["aiWorkflowPackRuntimeExecutionProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea AI workflow-pack runtime execution proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--lotus-ai-base-url", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-runtime-unavailable",
        action="store_true",
        help=(
            "Reserved for aggregate local automation. Runtime unavailability still emits no valid "
            "proof and cannot clear a readiness blocker."
        ),
    )
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
