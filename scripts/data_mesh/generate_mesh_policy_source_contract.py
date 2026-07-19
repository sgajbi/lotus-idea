# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.data_mesh.mesh_policy_source_contract import (  # noqa: E402
    build_mesh_policy_source_contract_payload,
    mesh_policy_source_contract_is_valid,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload  # noqa: E402
except ImportError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]  # noqa: E402
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the lotus-idea mesh policy source-contract artifact."
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
        payload = build_mesh_policy_source_contract_payload(
            generated_at_utc=generated_at_utc,
            repository_root=ROOT,
        )
        write_json_payload(payload, output=args.output)
        if not mesh_policy_source_contract_is_valid(payload):
            print("mesh policy source-contract artifact is invalid", file=sys.stderr)
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"mesh policy source-contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
