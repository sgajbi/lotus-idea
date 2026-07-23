# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.opportunity_archetype_evidence_pack import (
    build_canonical_opportunity_archetype_evidence_pack,
    opportunity_archetype_evidence_pack_is_valid,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_canonical_opportunity_archetype_evidence_pack(
            generated_at_utc=_parse_instant(args.generated_at_utc),
            repository_root=Path.cwd(),
        )
        write_json_payload(payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"opportunity archetype evidence pack generation error: {exc}", file=sys.stderr)
        return 2
    if not opportunity_archetype_evidence_pack_is_valid(payload):
        print("opportunity archetype evidence pack did not validate", file=sys.stderr)
        return 3
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe canonical opportunity archetype evidence pack."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    return parser


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    sys.exit(main())
