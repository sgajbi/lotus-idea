from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    MANIFEST_ENV,
    TIMEOUT_SECONDS_ENV,
)
from app.application.source_ingestion_worker import (
    source_ingestion_worker_plan_from_manifest,
    summarize_source_ingestion_worker_failure,
    summarize_source_ingestion_worker_run,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import CoreSourceEntitlementDenied, CoreSourceUnavailable
from app.repository_state import get_idea_repository, idea_repository_durable_storage_backed


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion worker configuration error: {exc}", file=sys.stderr)
        return 2

    if args.check_only:
        _write_json(plan.check_summary())
        return 0

    repository = get_idea_repository()
    try:
        core_base_url = _core_base_url(args)
        core_source = LotusCoreHighCashSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=core_base_url,
                    timeout_seconds=_timeout_seconds(args),
                )
            )
        )
        result = run_high_cash_source_ingestion_batch(
            plan.command,
            core_source=core_source,
            repository=repository,
        )
        _write_json(
            summarize_source_ingestion_worker_run(
                plan=plan,
                result=result,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
            )
        )
        return 0
    except CoreSourceEntitlementDenied:
        _write_json(
            summarize_source_ingestion_worker_failure(
                plan=plan,
                error_code="core_source_entitlement_denied",
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
            )
        )
        print("source ingestion worker blocked: core_source_entitlement_denied", file=sys.stderr)
        return 3
    except CoreSourceUnavailable as exc:
        _write_json(
            summarize_source_ingestion_worker_failure(
                plan=plan,
                error_code=exc.code,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
            )
        )
        print(f"source ingestion worker blocked: {exc.code}", file=sys.stderr)
        return 3
    except DownstreamServiceError as exc:
        _write_json(
            summarize_source_ingestion_worker_failure(
                plan=plan,
                error_code=exc.code,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
            )
        )
        print(f"source ingestion worker blocked: {exc.code}", file=sys.stderr)
        return 3
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion worker configuration error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or validate the lotus-idea high-cash source-ingestion worker manifest."
    )
    parser.add_argument("--manifest", default=os.getenv(MANIFEST_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate the worker manifest and print the planned bounded work without calling Core.",
    )
    return parser


def _manifest_path(args: argparse.Namespace) -> Path:
    if not args.manifest:
        raise ValueError(f"--manifest or {MANIFEST_ENV} is required")
    return Path(args.manifest)


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _core_base_url(args: argparse.Namespace) -> str:
    if not args.core_base_url:
        raise ValueError(f"--core-base-url or {CORE_BASE_URL_ENV} is required for run mode")
    return str(args.core_base_url)


def _timeout_seconds(args: argparse.Namespace) -> float:
    try:
        timeout = float(args.timeout_seconds)
    except ValueError as exc:
        raise ValueError("timeout seconds must be numeric") from exc
    if timeout <= 0:
        raise ValueError("timeout seconds must be positive")
    return timeout


def _write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
