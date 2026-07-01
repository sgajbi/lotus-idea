from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from app.application.mesh_policy_proof import (
    build_mesh_policy_proof_payload,
    mesh_policy_proof_is_valid,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc
except ModuleNotFoundError:
    from proof_generator_io import parse_generated_at_utc  # type: ignore[import-not-found,no-redef]


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the source-safe lotus-idea mesh policy proof artifact."
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument("--output", required=True, help="JSON output path.")
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        payload = build_mesh_policy_proof_payload(
            generated_at_utc=generated_at_utc,
            repository_root=ROOT,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
        if not mesh_policy_proof_is_valid(payload):
            print("mesh policy proof artifact is invalid", file=sys.stderr)
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"mesh policy proof error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
