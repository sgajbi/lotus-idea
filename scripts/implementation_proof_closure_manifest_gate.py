# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.implementation_proof_closure_manifest import (
    BLOCKER_CLOSURE_CONTRACT_PATH,
    blocker_closure_manifest_errors,
    blocker_closure_manifest_payload,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the RFC-0002 implementation-proof blocker closure manifest."
    )
    parser.add_argument(
        "--contract",
        default=str(ROOT / BLOCKER_CLOSURE_CONTRACT_PATH),
        help="Path to the blocker closure source contract.",
    )
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print the expanded current blocker manifest after validation.",
    )
    args = parser.parse_args(argv)
    contract_path = Path(args.contract)
    try:
        contract = _load_contract(contract_path)
        snapshot = build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=DEFAULT_EVALUATED_AT_UTC,
            repository=InMemoryIdeaRepository(),
            durable_storage_backed=False,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"implementation proof closure manifest error: {exc}", file=sys.stderr)
        return 2

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)
    if errors:
        print("\n".join(errors))
        return 1
    if args.print_manifest:
        print(
            json.dumps(
                blocker_closure_manifest_payload(snapshot=snapshot, contract=contract),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("Implementation proof closure manifest gate passed")
    return 0


def _load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("blocker closure manifest contract must be a JSON object")
    return payload


if __name__ == "__main__":
    sys.exit(main())
