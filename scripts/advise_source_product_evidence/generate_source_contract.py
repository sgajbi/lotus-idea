from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.application.advise_source_product_evidence import (  # noqa: E402
    PROFILES,
    build_advise_source_product_source_contract,
)

try:
    from scripts.proof_generator_io import (  # noqa: E402
        parse_generated_at_utc,
        write_json_payload,
    )
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef] # noqa: E402
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate closed typed Lotus Advise source-product evidence."
    )
    parser.add_argument("--capability", choices=tuple(PROFILES), required=True)
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--advise-root",
        help="Optional lotus-advise repository root; defaults to the sibling checkout.",
    )
    parser.add_argument("--output", required=True, help="JSON output path.")
    args = parser.parse_args(argv)
    try:
        payload = build_advise_source_product_source_contract(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            repository_root=ROOT,
            advise_root=Path(args.advise_root) if args.advise_root else None,
            profile=PROFILES[args.capability],
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError) as exc:
        print(f"Advise source-product evidence error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
