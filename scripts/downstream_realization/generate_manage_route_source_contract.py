# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
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

from app.application.downstream_realization.route_source_contract import (  # noqa: E402
    build_manage_route_source_contract_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload  # noqa: E402
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_manage_route_source_contract_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            manage_root=Path(args.manage_root) if args.manage_root else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Manage route source-contract error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    if payload["sourceContractValid"]:
        return 0
    if args.allow_missing_evidence and _source_file_evidence_is_missing(payload):
        return 0
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the digest-bound lotus-manage route source contract."
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


def _source_file_evidence_is_missing(payload: dict[str, object]) -> bool:
    source_authority = payload.get("sourceAuthority")
    return isinstance(source_authority, (list, tuple)) and any(
        isinstance(item, dict) and item.get("sha256") is None for item in source_authority
    )


if __name__ == "__main__":
    sys.exit(main())
