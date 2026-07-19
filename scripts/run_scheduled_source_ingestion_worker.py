# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.source_ingestion_readiness import (  # noqa: E402
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    MANIFEST_ENV,
    TIMEOUT_SECONDS_ENV,
)
from app.application.source_ingestion_scheduler import (  # noqa: E402
    DEFAULT_SCHEDULE_INTERVAL_SECONDS,
    DEFAULT_SCHEDULE_MAX_RUNS,
    SCHEDULE_INTERVAL_SECONDS_ENV,
    SCHEDULE_MAX_RUNS_ENV,
    SourceIngestionScheduleConfig,
    build_scheduled_worker_check_summary,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import source_ingestion_worker_plan_from_manifest  # noqa: E402
from run_source_ingestion_worker import main as run_once_worker_main  # noqa: E402


_stop_requested = False


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
        schedule = source_ingestion_schedule_config_from_values(
            interval_seconds=args.interval_seconds,
            max_runs=args.max_runs,
            run_forever=args.run_forever,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"scheduled source ingestion worker configuration error: {exc}", file=sys.stderr)
        return 2

    if args.check_only:
        _write_json(build_scheduled_worker_check_summary(plan=plan, schedule=schedule))
        return 0

    if not _core_source_urls_configured(args):
        print(
            "scheduled source ingestion worker configuration error: "
            f"--core-query-base-url/{CORE_QUERY_BASE_URL_ENV} and "
            f"--core-query-control-plane-base-url/{CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV} "
            f"are required, or --core-base-url/{CORE_BASE_URL_ENV} must provide a "
            "compatibility fallback",
            file=sys.stderr,
        )
        return 2

    return _run_schedule(args=args, schedule=schedule)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Run the lotus-idea high-cash source-ingestion worker on a bounded schedule.")
    )
    parser.add_argument("--manifest", default=os.getenv(MANIFEST_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--core-query-base-url", default=os.getenv(CORE_QUERY_BASE_URL_ENV))
    parser.add_argument(
        "--core-query-control-plane-base-url",
        default=os.getenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV),
    )
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument(
        "--interval-seconds",
        default=os.getenv(
            SCHEDULE_INTERVAL_SECONDS_ENV,
            str(DEFAULT_SCHEDULE_INTERVAL_SECONDS),
        ),
    )
    parser.add_argument(
        "--max-runs",
        default=os.getenv(SCHEDULE_MAX_RUNS_ENV, str(DEFAULT_SCHEDULE_MAX_RUNS)),
    )
    parser.add_argument(
        "--run-forever",
        action="store_true",
        default=False,
        help="Keep scheduling until the process receives SIGTERM or SIGINT.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate schedule and manifest without calling Core or writing repository state.",
    )
    return parser


def _run_once_args(args: argparse.Namespace) -> list[str]:
    run_args = [
        "--manifest",
        str(args.manifest),
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.core_base_url:
        run_args.extend(["--core-base-url", str(args.core_base_url)])
    if args.core_query_base_url:
        run_args.extend(["--core-query-base-url", str(args.core_query_base_url)])
    if args.core_query_control_plane_base_url:
        run_args.extend(
            [
                "--core-query-control-plane-base-url",
                str(args.core_query_control_plane_base_url),
            ]
        )
    return run_args


def _core_source_urls_configured(args: argparse.Namespace) -> bool:
    if args.core_base_url:
        return True
    return bool(args.core_query_base_url and args.core_query_control_plane_base_url)


def _run_schedule(*, args: argparse.Namespace, schedule: SourceIngestionScheduleConfig) -> int:
    global _stop_requested
    _stop_requested = False
    previous_handlers = _install_stop_handlers()
    exit_codes: list[int] = []
    iteration_index = 0
    try:
        while schedule.run_forever or iteration_index < schedule.max_runs:
            if _stop_requested:
                break
            _write_json(
                {
                    "schemaVersion": "lotus-idea.source-ingestion.scheduled-worker-iteration.v1",
                    "mode": "scheduled_iteration_started",
                    "iterationIndex": iteration_index,
                    "supportedFeaturePromoted": False,
                }
            )
            exit_code = run_once_worker_main(_run_once_args(args))
            exit_codes.append(exit_code)
            _write_json(
                {
                    "schemaVersion": "lotus-idea.source-ingestion.scheduled-worker-iteration.v1",
                    "mode": "scheduled_iteration_completed",
                    "iterationIndex": iteration_index,
                    "workerExitCode": exit_code,
                    "supportedFeaturePromoted": False,
                }
            )
            if exit_code != 0:
                return exit_code
            iteration_index += 1
            if _stop_requested or (
                not schedule.run_forever and iteration_index >= schedule.max_runs
            ):
                break
            time.sleep(schedule.interval_seconds)
    finally:
        _restore_stop_handlers(previous_handlers)
    return 0 if exit_codes else 2


def _install_stop_handlers() -> dict[int, Any]:
    previous_handlers: dict[int, Any] = {}
    for signal_number in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_handlers[signal_number] = signal.getsignal(signal_number)
            signal.signal(signal_number, _request_stop)
        except (OSError, RuntimeError, ValueError):
            continue
    return previous_handlers


def _restore_stop_handlers(previous_handlers: dict[int, Any]) -> None:
    for signal_number, handler in previous_handlers.items():
        try:
            signal.signal(signal_number, handler)
        except (OSError, RuntimeError, ValueError):
            continue


def _request_stop(_signal_number: int, _frame: Any) -> None:
    global _stop_requested
    _stop_requested = True


def _manifest_path(args: argparse.Namespace) -> Path:
    if not args.manifest:
        raise ValueError(f"--manifest or {MANIFEST_ENV} is required")
    return Path(args.manifest)


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
