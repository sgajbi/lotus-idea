# ruff: noqa: E402
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import UTC, date, datetime
import json
import os
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.performance_benchmark_readiness import (
    EvaluatePerformanceBenchmarkReadiness,
    evaluate_performance_benchmark_readiness,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (
    build_performance_benchmark_readiness_runtime_execution,
    performance_benchmark_readiness_runtime_execution_is_valid,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
)
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)

try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        timeout_seconds_from_args,
        write_json_payload,
    )

PERFORMANCE_BASE_URL_ENV = "LOTUS_PERFORMANCE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_PERFORMANCE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        command = _command(args)
        with closing(
            LotusPerformanceUnderperformanceSourceAdapter(
                DownstreamJsonClient(
                    DownstreamClientConfig(
                        base_url=_performance_base_url(args),
                        timeout_seconds=timeout_seconds_from_args(args),
                    )
                )
            )
        ) as source:
            result = evaluate_performance_benchmark_readiness(
                command,
                performance_source=source,
            )
        payload = build_performance_benchmark_readiness_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            result=result,
        )
        write_json_payload(payload, output=args.output)
        if performance_benchmark_readiness_runtime_execution_is_valid(payload):
            return 0
        blockers = payload["execution"]["qualificationBlockers"]
        print(
            "Performance benchmark-readiness runtime evidence did not qualify: "
            f"{','.join(blockers)}",
            file=sys.stderr,
        )
        return 3
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Performance benchmark-readiness runtime evidence configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


def _command(args: argparse.Namespace) -> EvaluatePerformanceBenchmarkReadiness:
    return EvaluatePerformanceBenchmarkReadiness(
        tenant_id=args.tenant_id,
        book_id=args.book_id,
        portfolio_id=args.portfolio_id,
        client_id=args.client_id,
        evaluation_id=args.evaluation_id,
        as_of_date=_parse_date(args.as_of_date, "as-of-date"),
        period_name=args.period_name,
        evaluated_at_utc=_parse_instant(args.evaluated_at_utc, "evaluated-at-utc"),
        reporting_currency=args.reporting_currency,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound Performance benchmark-readiness runtime evidence."
    )
    parser.add_argument("--performance-base-url", default=os.getenv(PERFORMANCE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--period-name", default="1Y")
    parser.add_argument("--reporting-currency")
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--output")
    return parser


def _performance_base_url(args: argparse.Namespace) -> str:
    value = str(args.performance_base_url or "").strip()
    if not value:
        raise ValueError(f"--performance-base-url or {PERFORMANCE_BASE_URL_ENV} is required")
    return value


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def _parse_instant(value: str, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    sys.exit(main())
