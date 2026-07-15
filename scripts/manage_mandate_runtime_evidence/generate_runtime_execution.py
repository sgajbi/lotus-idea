from __future__ import annotations

import argparse
from contextlib import closing
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.manage_mandate_runtime_evidence import (
    EvaluateManageMandateReadiness,
    build_manage_mandate_runtime_execution,
    evaluate_manage_mandate_readiness,
    manage_mandate_runtime_execution_is_valid,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
)
from app.infrastructure.lotus_manage_sources import LotusManageMandateHealthSourceAdapter

try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        timeout_seconds_from_args,
        write_json_payload,
    )

MANAGE_BASE_URL_ENV = "LOTUS_MANAGE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_MANAGE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        command = _command(args)
        with closing(
            LotusManageMandateHealthSourceAdapter(
                DownstreamJsonClient(
                    DownstreamClientConfig(
                        base_url=_manage_base_url(args),
                        timeout_seconds=timeout_seconds_from_args(args),
                    )
                )
            )
        ) as source:
            result = evaluate_manage_mandate_readiness(command, manage_source=source)
        payload = build_manage_mandate_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            result=result,
        )
        write_json_payload(payload, output=args.output)
        if manage_mandate_runtime_execution_is_valid(payload):
            return 0
        blockers = payload["execution"]["qualificationBlockers"]
        print(
            f"Manage mandate runtime evidence did not qualify: {','.join(blockers)}",
            file=sys.stderr,
        )
        return 3
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Manage mandate runtime evidence configuration error: {exc}", file=sys.stderr)
        return 2


def _command(args: argparse.Namespace) -> EvaluateManageMandateReadiness:
    return EvaluateManageMandateReadiness(
        tenant_id=args.tenant_id,
        portfolio_id=args.portfolio_id,
        as_of_date=_parse_date(args.as_of_date, "as-of-date"),
        evaluated_at_utc=_parse_instant(args.evaluated_at_utc, "evaluated-at-utc"),
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound Manage mandate-health runtime evidence."
    )
    parser.add_argument("--manage-base-url", default=os.getenv(MANAGE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
    parser.add_argument("--output")
    return parser


def _manage_base_url(args: argparse.Namespace) -> str:
    value = str(args.manage_base_url or "").strip()
    if not value:
        raise ValueError(f"--manage-base-url or {MANAGE_BASE_URL_ENV} is required")
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
