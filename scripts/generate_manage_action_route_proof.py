from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from app.application.downstream_route_contract_proof import (
    build_manage_action_route_proof_payload,
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
        payload = build_manage_action_route_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            manage_root=Path(args.manage_root) if args.manage_root else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"manage action route proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    if payload["manageActionRouteProofValid"]:
        return 0
    proof_checks = payload.get("proofChecks")
    if (
        args.allow_missing_evidence
        and isinstance(proof_checks, dict)
        and proof_checks.get("fileEvidencePresent") is False
    ):
        return 0
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe proof for the lotus-manage idea action route."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--manage-root")
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help=(
            "Write an invalid non-proof artifact and exit 0 when sibling lotus-manage "
            "evidence is absent. Contract drift still exits non-zero once required "
            "evidence files are present."
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
