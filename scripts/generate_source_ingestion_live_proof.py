from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.application.source_ingestion import run_high_cash_source_ingestion_batch
from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
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
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        core_base_url = _core_base_url(args)
        core_source = LotusCoreHighCashSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=core_base_url,
                    timeout_seconds=_timeout_seconds(args),
                )
            )
        )
        worker_summary = summarize_source_ingestion_worker_run(
            plan=plan,
            result=run_high_cash_source_ingestion_batch(
                plan.command,
                core_source=core_source,
                repository=repository,
            ),
            durable_storage_backed=durable_storage_backed,
        )
        proof_payload = build_source_ingestion_live_proof_payload(
            generated_at_utc=generated_at_utc,
            worker_summary=worker_summary,
            live_core_source_attempted=True,
        )
        _write_payload(proof_payload, output=args.output)
        return 0
    except (CoreSourceEntitlementDenied, CoreSourceUnavailable, DownstreamServiceError) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(_manifest_path(args)))
        repository = get_idea_repository()
        worker_summary = summarize_source_ingestion_worker_failure(
            plan=plan,
            error_code=error_code,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        proof_payload = build_source_ingestion_live_proof_payload(
            generated_at_utc=generated_at_utc,
            worker_summary=worker_summary,
            live_core_source_attempted=True,
        )
        _write_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source ingestion live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"source ingestion live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Core source-ingestion proof for lotus-idea."
    )
    parser.add_argument("--manifest", default=os.getenv(MANIFEST_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
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


def _core_base_url(args: argparse.Namespace) -> str:
    if not args.core_base_url:
        raise ValueError(f"--core-base-url or {CORE_BASE_URL_ENV} is required")
    return str(args.core_base_url)


def _timeout_seconds(args: argparse.Namespace) -> float:
    try:
        timeout = float(args.timeout_seconds)
    except ValueError as exc:
        raise ValueError("timeout seconds must be numeric") from exc
    if timeout <= 0:
        raise ValueError("timeout seconds must be positive")
    return timeout


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


def _write_payload(payload: dict[str, Any], *, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        return
    print(rendered)


if __name__ == "__main__":
    sys.exit(main())
