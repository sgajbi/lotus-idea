from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_ingestion_readiness import MANIFEST_ENV
from app.application.source_ingestion_scheduled_worker import (
    DOCKER_COMPOSE_WORKER_SERVICE,
    RUN_ONCE_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_ENTRYPOINT,
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deploy_proof_payload,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import source_ingestion_worker_plan_from_manifest
from run_scheduled_source_ingestion_worker import (
    SCHEDULE_INTERVAL_SECONDS_ENV,
    SCHEDULE_MAX_RUNS_ENV,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(args.manifest))
        schedule = source_ingestion_schedule_config_from_values(
            interval_seconds=args.interval_seconds,
            max_runs=args.max_runs,
            run_forever=args.run_forever,
        )
        check_summary = build_scheduled_worker_check_summary(plan=plan, schedule=schedule)
        payload = build_scheduled_worker_deploy_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            check_summary=check_summary,
            scheduler_entrypoint_present=(ROOT / SCHEDULED_WORKER_ENTRYPOINT).is_file(),
            run_once_worker_entrypoint_present=(ROOT / RUN_ONCE_WORKER_ENTRYPOINT).is_file(),
            docker_compose_service_present=_docker_compose_service_present(),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"scheduled source ingestion worker proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0 if payload["scheduledWorkerDeployProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea scheduled source-ingestion worker proof."
    )
    parser.add_argument("--manifest", default=os.getenv(MANIFEST_ENV), required=False)
    parser.add_argument(
        "--interval-seconds",
        default=os.getenv(SCHEDULE_INTERVAL_SECONDS_ENV, "300"),
    )
    parser.add_argument("--max-runs", default=os.getenv(SCHEDULE_MAX_RUNS_ENV, "1"))
    parser.add_argument(
        "--run-forever",
        action="store_true",
        help="Record that the deployed scheduler runs until a controlled stop.",
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    return parser


def _read_manifest(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        raise ValueError(f"--manifest or {MANIFEST_ENV} is required")
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _docker_compose_service_present() -> bool:
    compose_path = ROOT / "docker-compose.yml"
    try:
        compose_text = compose_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        DOCKER_COMPOSE_WORKER_SERVICE in compose_text
        and SCHEDULED_WORKER_ENTRYPOINT in compose_text
    )


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
