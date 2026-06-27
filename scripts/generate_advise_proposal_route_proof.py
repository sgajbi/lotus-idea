from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from app.application.downstream_route_contract_proof import (
    build_advise_proposal_route_proof_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_advise_proposal_route_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            advise_root=Path(args.advise_root) if args.advise_root else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"advise proposal route proof error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    if payload["adviseProposalRouteProofValid"]:
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
        description="Generate a source-safe proof for the lotus-advise idea proposal route."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--advise-root")
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help=(
            "Write an invalid non-proof artifact and exit 0 when sibling lotus-advise "
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
