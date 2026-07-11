from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

from app.application.lotus_ai_attestation_contract_proof import (
    build_lotus_ai_attestation_contract_proof,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the source-safe local Lotus AI attestation contract proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--lotus-ai-root")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        generated_at_utc = datetime.fromisoformat(args.generated_at_utc.replace("Z", "+00:00"))
        if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
            raise ValueError("--generated-at-utc must be timezone-aware")
        payload = build_lotus_ai_attestation_contract_proof(
            generated_at_utc=generated_at_utc,
            repository_root=ROOT,
            lotus_ai_root=Path(args.lotus_ai_root) if args.lotus_ai_root else None,
        )
    except (OSError, ValueError) as exc:
        print(f"Lotus AI attestation contract proof error: {exc}", file=sys.stderr)
        return 2
    write_json_payload(payload, output=args.output)
    return 0 if payload["localContractProofValid"] else 1


if __name__ == "__main__":
    sys.exit(main())
