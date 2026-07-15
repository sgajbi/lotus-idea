from __future__ import annotations

import argparse
from contextlib import closing
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.low_income_cashflow_runtime_evidence import (
    EvaluateLowIncomeCashflowReadiness,
    build_blocked_low_income_cashflow_runtime_execution,
    build_low_income_cashflow_runtime_execution,
    evaluate_low_income_cashflow_readiness,
    low_income_cashflow_runtime_execution_is_valid,
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
        core_query_base_url_from_args,
        timeout_seconds_from_args,
        write_json_payload,
    )
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        core_query_base_url_from_args,
        timeout_seconds_from_args,
        write_json_payload,
    )

CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
CORE_QUERY_BASE_URL_ENV = "LOTUS_CORE_QUERY_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_CORE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: EvaluateLowIncomeCashflowReadiness | None = None
    try:
        generated_at = _parse_instant(args.generated_at_utc, "generated-at-utc")
        command = _command(args)
        with closing(
            LotusCoreHighCashSourceAdapter(
                DownstreamJsonClient(
                    DownstreamClientConfig(
                        base_url=core_query_base_url_from_args(
                            args,
                            query_env=CORE_QUERY_BASE_URL_ENV,
                            base_env=CORE_BASE_URL_ENV,
                        ),
                        timeout_seconds=timeout_seconds_from_args(args),
                    )
                )
            )
        ) as source:
            result = evaluate_low_income_cashflow_readiness(command, core_source=source)
        payload = build_low_income_cashflow_runtime_execution(
            generated_at_utc=generated_at,
            result=result,
        )
        write_json_payload(payload, output=args.output)
        if low_income_cashflow_runtime_execution_is_valid(payload):
            return 0
        print("Low-income cashflow runtime evidence did not qualify", file=sys.stderr)
        return 3
    except (CoreSourceEntitlementDenied, CoreSourceUnavailable, DownstreamServiceError) as exc:
        return _write_blocked(args=args, command=command, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Low-income cashflow runtime evidence configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked(
    *,
    args: argparse.Namespace,
    command: EvaluateLowIncomeCashflowReadiness | None,
    error_code: str,
) -> int:
    try:
        active_command = command or _command(args)
        payload = build_blocked_low_income_cashflow_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            command=active_command,
            error_code=error_code,
        )
        write_json_payload(payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Low-income cashflow runtime evidence error: {exc}", file=sys.stderr)
        return 2
    print(f"Low-income cashflow runtime evidence blocked: {error_code}", file=sys.stderr)
    return 3


def _command(args: argparse.Namespace) -> EvaluateLowIncomeCashflowReadiness:
    return EvaluateLowIncomeCashflowReadiness(
        tenant_id=args.tenant_id,
        portfolio_id=args.portfolio_id,
        as_of_date=_parse_date(args.as_of_date, "as-of-date"),
        evaluated_at_utc=_parse_instant(args.evaluated_at_utc, "evaluated-at-utc"),
        horizon_days=args.horizon_days,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound Core low-income cashflow runtime evidence."
    )
    parser.add_argument("--core-query-base-url", default=os.getenv(CORE_QUERY_BASE_URL_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--horizon-days", type=int, default=30)
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
    return str(getattr(exc, "code", "")).strip() or "core_cashflow_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
