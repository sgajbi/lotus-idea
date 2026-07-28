# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.full_live_opportunity_journey_proof import (
    build_full_live_opportunity_journey_proof_payload,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        repository_root = Path(__file__).resolve().parents[1]
        gateway_workbench_runtime_execution_proof = (
            _read_json_object(Path(args.gateway_workbench_runtime_execution_proof))
            if args.gateway_workbench_runtime_execution_proof
            else None
        )
        payload = build_full_live_opportunity_journey_proof_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            repository_root=repository_root,
            implementation_proof_readiness=_read_json_object(
                Path(args.implementation_proof_readiness)
            ),
            implementation_proof_readiness_ref=args.implementation_proof_readiness_ref,
            gateway_workbench_runtime_execution_proof=gateway_workbench_runtime_execution_proof,
            gateway_workbench_runtime_execution_proof_ref=(
                args.gateway_workbench_runtime_execution_proof_ref
            ),
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"full-live opportunity journey proof error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate RFC-0002 full live opportunity journey aggregate proof."
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-07-28T00:00:00Z.",
    )
    parser.add_argument(
        "--implementation-proof-readiness",
        required=True,
        help="Path to a generated implementation-proof readiness snapshot.",
    )
    parser.add_argument(
        "--implementation-proof-readiness-ref",
        default="output/implementation-proof/readiness-current.json",
        help="Source-safe reference for the readiness snapshot.",
    )
    parser.add_argument(
        "--gateway-workbench-runtime-execution-proof",
        help="Optional path to the Gateway/Workbench runtime execution proof.",
    )
    parser.add_argument(
        "--gateway-workbench-runtime-execution-proof-ref",
        default="output/workbench/gateway-workbench-runtime-execution-proof.json",
        help="Source-safe reference for the Gateway/Workbench runtime execution proof.",
    )
    parser.add_argument("--output", help="Optional JSON output path.")
    return parser


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


if __name__ == "__main__":
    sys.exit(main())
