from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path

from app.application.missing_risk_profile_source_product_proof import (
    build_missing_risk_profile_source_product_proof_payload,
)


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
            generated_at_utc=_parse_utc(args.generated_at_utc),
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


def _parse_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    sys.exit(main())
