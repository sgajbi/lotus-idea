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
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
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
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)

CORE_BASE_URL_HELP = (
    f"Optional compatibility Core base URL used for both Core query and query-control-plane "
    f"clients. Prefer --core-query-base-url and --core-query-control-plane-base-url for the "
    f"canonical split Core runtime. Defaults to {CORE_BASE_URL_ENV}."
)


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
        core_query_base_url, core_query_control_plane_base_url = _core_source_base_urls(args)
        timeout_seconds = _timeout_seconds(args)
        core_source = LotusCoreHighCashSourceAdapter(
            query_client=DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=core_query_base_url,
                    timeout_seconds=timeout_seconds,
                )
            ),
            query_control_plane_client=DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=core_query_control_plane_base_url,
                    timeout_seconds=timeout_seconds,
                )
            ),
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
    parser.add_argument(
        "--core-base-url", default=os.getenv(CORE_BASE_URL_ENV), help=CORE_BASE_URL_HELP
    )
    parser.add_argument(
        "--core-query-base-url",
        default=os.getenv(CORE_QUERY_BASE_URL_ENV),
        help=f"Core query-service base URL. Defaults to {CORE_QUERY_BASE_URL_ENV}.",
    )
    parser.add_argument(
        "--core-query-control-plane-base-url",
        default=os.getenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV),
        help=(
            "Core query-control-plane service base URL. Defaults to "
            f"{CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV}."
        ),
    )
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


def _core_source_base_urls(args: argparse.Namespace) -> tuple[str, str]:
    query_base_url = str(args.core_query_base_url or args.core_base_url or "").strip()
    query_control_plane_base_url = str(
        args.core_query_control_plane_base_url or args.core_base_url or ""
    ).strip()
    missing: list[str] = []
    if not query_base_url:
        missing.append(f"--core-query-base-url or {CORE_QUERY_BASE_URL_ENV}")
    if not query_control_plane_base_url:
        missing.append(
            f"--core-query-control-plane-base-url or {CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV}"
        )
    if missing:
        missing.append(f"or compatibility --core-base-url/{CORE_BASE_URL_ENV}")
        raise ValueError("Core source URLs are required for run mode: " + ", ".join(missing))
    return query_base_url, query_control_plane_base_url


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
