from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.core_benchmark_assignment_runtime_evidence import (
    EvaluateCoreBenchmarkAssignmentReadiness,
    build_blocked_core_benchmark_assignment_runtime_execution,
    build_core_benchmark_assignment_runtime_execution,
    core_benchmark_assignment_runtime_execution_is_valid,
    evaluate_core_benchmark_assignment_readiness,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import CoreSourceEntitlementDenied, CoreSourceUnavailable

try:
    from scripts.proof_generator_io import (
        core_control_plane_base_url_from_args,
        timeout_seconds_from_args,
        write_json_payload,
    )
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        core_control_plane_base_url_from_args,
        timeout_seconds_from_args,
        write_json_payload,
    )

CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV = "LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_CORE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: EvaluateCoreBenchmarkAssignmentReadiness | None = None
    try:
        generated_at = _parse_instant(args.generated_at_utc, "generated-at-utc")
        command = _command(args)
        source = LotusCoreHighCashSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=core_control_plane_base_url_from_args(
                        args,
                        control_plane_env=CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
                        base_env=CORE_BASE_URL_ENV,
                    ),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        result = evaluate_core_benchmark_assignment_readiness(command, core_source=source)
        payload = build_core_benchmark_assignment_runtime_execution(
            generated_at_utc=generated_at, result=result
        )
        write_json_payload(payload, output=args.output)
        if core_benchmark_assignment_runtime_execution_is_valid(payload):
            return 0
        print("Core benchmark-assignment runtime evidence did not qualify", file=sys.stderr)
        return 3
    except (CoreSourceEntitlementDenied, CoreSourceUnavailable, DownstreamServiceError) as exc:
        return _write_blocked(args=args, command=command, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Core benchmark-assignment runtime evidence configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


def _write_blocked(
    *,
    args: argparse.Namespace,
    command: EvaluateCoreBenchmarkAssignmentReadiness | None,
    error_code: str,
) -> int:
    try:
        active_command = command or _command(args)
        payload = build_blocked_core_benchmark_assignment_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            command=active_command,
            error_code=error_code,
        )
        write_json_payload(payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Core benchmark-assignment runtime evidence error: {exc}", file=sys.stderr)
        return 2
    print(f"Core benchmark-assignment runtime evidence blocked: {error_code}", file=sys.stderr)
    return 3


def _command(args: argparse.Namespace) -> EvaluateCoreBenchmarkAssignmentReadiness:
    return EvaluateCoreBenchmarkAssignmentReadiness(
        tenant_id=args.tenant_id,
        portfolio_id=args.portfolio_id,
        as_of_date=_parse_date(args.as_of_date, "as-of-date"),
        evaluated_at_utc=_parse_instant(args.evaluated_at_utc, "evaluated-at-utc"),
        reporting_currency=args.reporting_currency,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound Core benchmark-assignment runtime evidence."
    )
    parser.add_argument(
        "--core-query-control-plane-base-url",
        default=os.getenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV),
    )
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--reporting-currency")
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
    parser.add_argument("--output")
    return parser


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


def _source_error_code(exc: Exception) -> str:
    if isinstance(exc, CoreSourceEntitlementDenied):
        return "core_source_entitlement_denied"
    return str(getattr(exc, "code", "")).strip() or "core_benchmark_assignment_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
