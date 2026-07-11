from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import sys

from app.application.downstream_capacity_seed import (
    SeedDownstreamCapacityResourceCommand,
    build_downstream_capacity_seed_artifact,
    seed_downstream_capacity_resource,
)
from app.infrastructure.http_downstream_capacity_seed import HttpDownstreamCapacitySeed


AUTHORIZATION_ENV = "LOTUS_IDEA_CAPACITY_AUTHORIZATION"
TRUSTED_CONTEXT_ENV = "LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed one isolated synthetic Idea resource for downstream capacity runs."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--seeded-at-utc", type=_parse_datetime, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapter: HttpDownstreamCapacitySeed | None = None
    try:
        if args.confirmation != "SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE":
            raise ValueError("synthetic capacity seed confirmation is required")
        if args.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        adapter = HttpDownstreamCapacitySeed(
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            base_headers=_base_headers(),
        )
        result = seed_downstream_capacity_resource(
            SeedDownstreamCapacityResourceCommand(
                run_id=args.run_id,
                as_of_date=args.as_of_date,
                seeded_at_utc=args.seeded_at_utc,
            ),
            port=adapter,
        )
        artifact = build_downstream_capacity_seed_artifact(
            result,
            generated_at_utc=datetime.now(UTC),
            commit_sha=args.commit_sha,
            branch=args.branch,
            run_id=args.run_id,
        )
        _write_json_atomic(args.output, artifact)
        return 0
    except (OSError, ValueError) as exc:
        print(f"downstream capacity seed failed: {exc}", file=sys.stderr)
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
