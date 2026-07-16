from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from app.application.source_ingestion_readiness import MANIFEST_ENV
from app.application.source_ingestion_scheduler import (
    SCHEDULE_INTERVAL_SECONDS_ENV,
    SCHEDULE_MAX_RUNS_ENV,
    build_scheduled_worker_check_summary,
    build_scheduled_worker_source_contract_payload,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import source_ingestion_worker_plan_from_manifest
from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(args.manifest))
        schedule = source_ingestion_schedule_config_from_values(
            interval_seconds=args.interval_seconds,
            max_runs=args.max_runs,
            run_forever=args.run_forever,
        )
        payload = build_scheduled_worker_source_contract_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            check_summary=build_scheduled_worker_check_summary(
                plan=plan,
                schedule=schedule,
            ),
            repository_root=ROOT,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"scheduled worker source-contract error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate digest-bound source-contract evidence for the scheduled "
            "source-ingestion worker."
        )
    )
    parser.add_argument("--manifest", default=os.getenv(MANIFEST_ENV))
    parser.add_argument(
        "--interval-seconds",
        default=os.getenv(SCHEDULE_INTERVAL_SECONDS_ENV, "300"),
    )
    parser.add_argument("--max-runs", default=os.getenv(SCHEDULE_MAX_RUNS_ENV, "1"))
    parser.add_argument("--run-forever", action="store_true")
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    return parser


def _read_manifest(path_value: str | None) -> dict[str, object]:
    if not path_value:
        raise ValueError(f"--manifest or {MANIFEST_ENV} is required")
    payload = json.loads(Path(path_value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


if __name__ == "__main__":
    sys.exit(main())
