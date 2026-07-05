from __future__ import annotations

import argparse
import sys

from app.application.mandate_restriction_source_product_proof import (
    build_mandate_restriction_source_product_proof_payload,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate source-safe Advise mandate/restriction source-product proof."
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument("--output", required=True, help="JSON output path.")
    args = parser.parse_args(argv)
    try:
        payload = build_mandate_restriction_source_product_proof_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError) as exc:
        print(f"mandate/restriction source-product proof error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
