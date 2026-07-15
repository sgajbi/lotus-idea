from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.concentration_risk_signal import (
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
    EvaluateConcentrationRiskFromRiskCommand,
    evaluate_and_persist_concentration_risk_signal_from_risk,
)
from app.application.risk_concentration_runtime_evidence import (
    build_blocked_risk_concentration_runtime_execution,
    build_risk_concentration_runtime_execution,
    risk_concentration_runtime_execution_is_valid,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_risk_sources import LotusRiskConcentrationSourceAdapter
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

RISK_BASE_URL_ENV = "LOTUS_RISK_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_RISK_TIMEOUT_SECONDS"
ACTOR_SUBJECT = "lotus-idea-risk-concentration-runtime-evidence"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand | None = None
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        command = _command(args)
        repository = get_idea_repository()
        source = LotusRiskConcentrationSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_risk_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        result = evaluate_and_persist_concentration_risk_signal_from_risk(
            command,
            risk_source=source,
            repository=repository,
        )
        payload = build_risk_concentration_runtime_execution(
            generated_at_utc=generated_at_utc,
            command=command,
            result=result,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        write_json_payload(payload, output=args.output)
        if risk_concentration_runtime_execution_is_valid(payload):
            return 0
        print("risk concentration runtime evidence did not qualify", file=sys.stderr)
        return 3
    except (DownstreamClientConfigurationError, DownstreamServiceError) as exc:
        return _write_blocked(args=args, command=command, error_code=_source_error_code(exc))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"risk concentration runtime evidence configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked(
    *,
    args: argparse.Namespace,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand | None,
    error_code: str,
) -> int:
    try:
        active_command = command or _command(args)
        repository = get_idea_repository()
        payload = build_blocked_risk_concentration_runtime_execution(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            command=active_command,
            error_code=error_code,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        write_json_payload(payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"risk concentration runtime evidence error: {exc}", file=sys.stderr)
        return 2
    print(f"risk concentration runtime evidence blocked: {error_code}", file=sys.stderr)
    return 3


def _command(args: argparse.Namespace) -> EvaluateAndPersistConcentrationRiskFromRiskCommand:
    portfolio_id = str(args.portfolio_id).strip()
    as_of_date = _parse_date(args.as_of_date, "as-of-date")
    evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
    idempotency_key = str(args.idempotency_key or "").strip() or (
        f"runtime-evidence:risk-concentration:{portfolio_id}:{as_of_date.isoformat()}"
    )
    return EvaluateAndPersistConcentrationRiskFromRiskCommand(
        evaluation=EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            evaluated_at_utc=evaluated_at_utc,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
        ),
        idempotency_key=idempotency_key,
        actor_subject=ACTOR_SUBJECT,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe Lotus Risk concentration runtime execution evidence."
    )
    parser.add_argument("--risk-base-url", default=os.getenv(RISK_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--idempotency-key")
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
    parser.add_argument("--output")
    return parser


def _risk_base_url(args: argparse.Namespace) -> str:
    value = str(args.risk_base_url or "").strip()
    if not value:
        raise ValueError(f"--risk-base-url or {RISK_BASE_URL_ENV} is required")
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
    return str(code).strip() or "risk_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
