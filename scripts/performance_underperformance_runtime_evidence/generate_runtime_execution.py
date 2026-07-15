from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
from decimal import Decimal
import json
import os
import sys

from app.application.performance_underperformance_runtime_evidence import (
    build_blocked_performance_underperformance_runtime_execution,
    build_performance_underperformance_runtime_execution,
    performance_underperformance_runtime_execution_is_valid,
)
from app.application.underperformance_signal import (
    DEFAULT_UNDERPERFORMANCE_POLICY,
    EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    EvaluateUnderperformanceFromPerformanceCommand,
    evaluate_and_persist_underperformance_signal_from_performance,
)
from app.domain import UnderperformanceSignalPolicy
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
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
ACTOR_SUBJECT = "lotus-idea-performance-underperformance-runtime-evidence"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: EvaluateAndPersistUnderperformanceFromPerformanceCommand | None = None
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        command = _command(args)
        repository = get_idea_repository()
        source = LotusPerformanceUnderperformanceSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_performance_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        result = evaluate_and_persist_underperformance_signal_from_performance(
            command,
            performance_source=source,
            repository=repository,
            policy=_policy(args),
        )
        payload = build_performance_underperformance_runtime_execution(
            generated_at_utc=generated_at_utc,
            command=command,
            result=result,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        write_json_payload(payload, output=args.output)
        if performance_underperformance_runtime_execution_is_valid(payload):
            return 0
        print("performance underperformance runtime evidence did not qualify", file=sys.stderr)
        return 3
    except (DownstreamClientConfigurationError, DownstreamServiceError) as exc:
        return _write_blocked(args=args, command=command, error_code=_source_error_code(exc))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"performance underperformance runtime evidence configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


def _write_blocked(
    *,
    args: argparse.Namespace,
    command: EvaluateAndPersistUnderperformanceFromPerformanceCommand | None,
    error_code: str,
) -> int:
    try:
        active_command = command or _command(args)
        repository = get_idea_repository()
        payload = build_blocked_performance_underperformance_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            command=active_command,
            error_code=error_code,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        write_json_payload(payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"performance underperformance runtime evidence error: {exc}", file=sys.stderr)
        return 2
    print(f"performance underperformance runtime evidence blocked: {error_code}", file=sys.stderr)
    return 3


def _command(
    args: argparse.Namespace,
) -> EvaluateAndPersistUnderperformanceFromPerformanceCommand:
    portfolio_id = str(args.portfolio_id).strip()
    as_of_date = _parse_date(args.as_of_date, "as-of-date")
    evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
    period_name = str(args.period_name).strip()
    if not portfolio_id or not period_name:
        raise ValueError("portfolio-id and period-name are required")
    idempotency_key = str(args.idempotency_key or "").strip() or (
        "runtime-evidence:performance-underperformance:"
        f"{portfolio_id}:{as_of_date.isoformat()}:{period_name}"
    )
    return EvaluateAndPersistUnderperformanceFromPerformanceCommand(
        evaluation=EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            period_name=period_name,
            evaluated_at_utc=evaluated_at_utc,
            reporting_currency=args.reporting_currency,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
        ),
        idempotency_key=idempotency_key,
        actor_subject=ACTOR_SUBJECT,
    )


def _policy(args: argparse.Namespace) -> UnderperformanceSignalPolicy:
    return UnderperformanceSignalPolicy(
        policy_version=DEFAULT_UNDERPERFORMANCE_POLICY.policy_version,
        active_return_threshold=Decimal(args.active_return_threshold),
        candidate_score=DEFAULT_UNDERPERFORMANCE_POLICY.candidate_score,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe Performance underperformance runtime execution evidence."
    )
    parser.add_argument("--performance-base-url", default=os.getenv(PERFORMANCE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--period-name", default="YTD")
    parser.add_argument("--reporting-currency")
    parser.add_argument("--active-return-threshold", default="-0.005")
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--idempotency-key")
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
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


def _source_error_code(exc: Exception) -> str:
    code = getattr(exc, "code", "")
    return str(code).strip() or "performance_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
