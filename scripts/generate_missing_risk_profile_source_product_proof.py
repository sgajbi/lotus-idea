from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.application.missing_risk_profile_source_product_proof import (
    build_missing_risk_profile_source_product_proof_payload,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc
except ModuleNotFoundError:
    from proof_generator_io import parse_generated_at_utc  # type: ignore[import-not-found,no-redef]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate source-safe Advise risk-profile source-product proof."
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument("--output", required=True, help="JSON output path.")
    args = parser.parse_args(argv)
    try:
        payload = build_missing_risk_profile_source_product_proof_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
        return 0
    except (OSError, ValueError) as exc:
        print(f"missing risk-profile source-product proof error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
