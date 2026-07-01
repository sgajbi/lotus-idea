from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.performance_underperformance_live_proof import (
    build_performance_underperformance_live_proof_payload,
)
from app.application.underperformance_signal import (
    DEFAULT_UNDERPERFORMANCE_POLICY,
    EvaluateUnderperformanceSignalCommand,
    EvaluateUnderperformanceFromPerformanceCommand,
    evaluate_underperformance_signal_command,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)
from app.ports.performance_sources import (
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidenceRequest,
)


try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import timeout_seconds_from_args, write_json_payload  # type: ignore[import-not-found,no-redef]

PERFORMANCE_BASE_URL_ENV = "LOTUS_PERFORMANCE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_PERFORMANCE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        performance_source = LotusPerformanceUnderperformanceSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_performance_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        command = EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id=args.portfolio_id,
            as_of_date=_parse_date(args.as_of_date, "as-of-date"),
            period_name=args.period_name,
            reporting_currency=args.reporting_currency,
            evaluated_at_utc=evaluated_at_utc,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
        )
        request = PerformanceUnderperformanceEvidenceRequest(
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            period_name=command.period_name,
            evaluated_at_utc=command.evaluated_at_utc,
            active_return_threshold=DEFAULT_UNDERPERFORMANCE_POLICY.active_return_threshold,
            reporting_currency=command.reporting_currency,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
        evidence = performance_source.fetch_underperformance_evidence(request)
        evaluation = evaluate_underperformance_signal_command(
            EvaluateUnderperformanceSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_active_return=evidence.source_reported_active_return,
                benchmark_context_available=evidence.benchmark_context_available,
                performance_ref=evidence.performance_ref,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=evidence.entitlement_allowed,
            )
        )
        proof_payload = build_performance_underperformance_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_performance_source_attempted=True,
            evaluation_summary=_evaluation_summary(evaluation, evidence=evidence),
        )
        write_json_payload(proof_payload, output=args.output)
        return 0
    except (
        PerformanceSourceEntitlementDenied,
        PerformanceSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"performance underperformance live proof configuration error: {exc}", file=sys.stderr
        )
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_performance_underperformance_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_performance_source_attempted=True,
            evaluation_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-performance",
                "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
                "errorCode": error_code,
                "sourceDiagnosticCodes": [error_code],
                "reasonCodes": [],
                "unsupportedReasons": ["source_unavailable"],
                "sourceEvidenceCurrent": False,
                "benchmarkContextAvailable": False,
            },
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"performance underperformance live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"performance underperformance live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate source-safe live Lotus Performance underperformance proof for lotus-idea."
        )
    )
    parser.add_argument("--performance-base-url", default=os.getenv(PERFORMANCE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--period-name", default="1Y")
    parser.add_argument("--reporting-currency")
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware proof instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        required=True,
        help="Timezone-aware evaluation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
    parser.add_argument(
        "--output",
        help="Optional proof JSON output path. Parent directories are created when needed.",
    )
    return parser


def _evaluation_summary(
    evaluation: SignalEvaluationResult,
    *,
    evidence: object,
) -> dict[str, object]:
    performance_ref = getattr(evidence, "performance_ref", None)
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-performance",
        "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
        "evaluationOutcome": evaluation.outcome.value,
        "sourceEvidenceCurrent": (
            performance_ref is not None and performance_ref.freshness is EvidenceFreshness.CURRENT
        ),
        "benchmarkContextAvailable": bool(getattr(evidence, "benchmark_context_available", False)),
        "reasonCodes": [reason_code.value for reason_code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "sourceDiagnosticCodes": (
            [str(getattr(evidence, "performance_diagnostic"))]
            if getattr(evidence, "performance_diagnostic", None)
            else []
        ),
    }


def _performance_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.performance_base_url or "").strip()
    if not base_url:
        raise ValueError(f"--performance-base-url or {PERFORMANCE_BASE_URL_ENV} is required")
    return base_url


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
    if isinstance(exc, PerformanceSourceEntitlementDenied):
        return "performance_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "performance_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
