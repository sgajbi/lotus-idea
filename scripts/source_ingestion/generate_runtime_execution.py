# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_runtime_evidence import (
    build_blocked_source_ingestion_runtime_execution,
    build_source_ingestion_runtime_execution,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    MANIFEST_ENV,
    TIMEOUT_SECONDS_ENV,
)
from app.application.source_ingestion_worker import (
    source_ingestion_worker_plan_from_manifest,
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

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from proof_generator_io import timeout_seconds_from_args, write_json_payload  # noqa: E402

CORE_BASE_URL_HELP = (
    f"Optional compatibility Core base URL used for both Core query and query-control-plane "
    f"clients. Prefer --core-query-base-url and --core-query-control-plane-base-url for live "
    f"proof against the canonical split Core runtime. Defaults to {CORE_BASE_URL_ENV}."
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        core_query_base_url, core_query_control_plane_base_url = _core_source_base_urls(args)
        timeout_seconds = timeout_seconds_from_args(args)
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
        proof_payload = build_source_ingestion_runtime_execution(
            generated_at_utc=generated_at_utc,
            plan=plan,
            result=result,
            durable_storage_backed=durable_storage_backed,
        )
        write_json_payload(proof_payload, output=args.output)
        return 0
    except (CoreSourceEntitlementDenied, CoreSourceUnavailable, DownstreamServiceError) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion runtime evidence configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
        repository = get_idea_repository()
        proof_payload = build_blocked_source_ingestion_runtime_execution(
            generated_at_utc=generated_at_utc,
            plan=plan,
            error_code=error_code,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion runtime evidence error: {exc}", file=sys.stderr)
        return 2
    print(f"source ingestion runtime evidence blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe Core source-ingestion runtime execution evidence."
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
        "--generated-at-utc",
        required=True,
        help="Timezone-aware proof instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--output",
        help="Optional proof JSON output path. Parent directories are created when needed.",
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
        raise ValueError("Core source URLs are required: " + ", ".join(missing))
    return query_base_url, query_control_plane_base_url


def _parse_instant(value: str, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _source_error_code(exc: Exception) -> str:
    if isinstance(exc, CoreSourceEntitlementDenied):
        return "core_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "core_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
