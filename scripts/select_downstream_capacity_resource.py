# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_capacity_resource import (
    SelectDownstreamCapacityResourceCommand,
    build_downstream_capacity_resource_artifact,
    select_downstream_capacity_resource,
)
from app.infrastructure.http_downstream_capacity_resource import HttpDownstreamCapacityResource


AUTHORIZATION_ENV = "LOTUS_IDEA_CAPACITY_AUTHORIZATION"
TRUSTED_CONTEXT_ENV = "LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select either one fresh authorized Idea conversion intent or one retained accepted "
            "submission for bounded, non-certifying downstream proof."
        )
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--accepted-not-before-utc", type=_parse_datetime)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapter: HttpDownstreamCapacityResource | None = None
    try:
        if args.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        adapter = HttpDownstreamCapacityResource(
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            base_headers=_base_headers(),
        )
        result = select_downstream_capacity_resource(
            SelectDownstreamCapacityResourceCommand(
                candidate_id=args.candidate_id,
                tenant_id=args.tenant_id,
                book_id=args.book_id,
                portfolio_id=args.portfolio_id,
                client_id=args.client_id,
                accepted_not_before_utc=args.accepted_not_before_utc,
            ),
            port=adapter,
        )
        artifact = build_downstream_capacity_resource_artifact(
            result,
            generated_at_utc=datetime.now(UTC),
            commit_sha=args.commit_sha,
            branch=args.branch,
            run_id=args.run_id,
        )
        _write_json_atomic(args.output, artifact)
        return 0
    except (OSError, ValueError) as exc:
        print(f"downstream capacity resource selection failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if adapter is not None:
            adapter.close()


def _base_headers() -> dict[str, str]:
    values = {
        "Authorization": os.getenv(AUTHORIZATION_ENV, "").strip(),
        "X-Lotus-Trusted-Caller-Context": os.getenv(TRUSTED_CONTEXT_ENV, "").strip(),
    }
    return {key: value for key, value in values.items() if value}


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parse_datetime(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
