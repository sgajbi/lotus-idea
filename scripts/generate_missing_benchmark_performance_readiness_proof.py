from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys
from pathlib import Path

from app.application.missing_benchmark_performance_readiness_proof import (
    build_missing_benchmark_performance_readiness_proof_payload,
)
from app.domain import EvidenceFreshness
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
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
)


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
                    timeout_seconds=_timeout_seconds(args),
                )
            )
        )
        evidence = performance_source.fetch_benchmark_readiness_evidence(
            PerformanceBenchmarkReadinessEvidenceRequest(
                portfolio_id=args.portfolio_id,
                as_of_date=_parse_date(args.as_of_date, "as-of-date"),
                period_name=args.period_name,
                evaluated_at_utc=evaluated_at_utc,
                reporting_currency=args.reporting_currency,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        proof_payload = build_missing_benchmark_performance_readiness_proof_payload(
            generated_at_utc=generated_at_utc,
            live_performance_source_attempted=True,
            performance_summary=_performance_summary(evidence),
        )
        _write_payload(proof_payload, output=args.output)
        return 0
    except (
        PerformanceSourceEntitlementDenied,
        PerformanceSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"missing benchmark performance readiness proof configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_missing_benchmark_performance_readiness_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_performance_source_attempted=True,
            performance_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-performance",
                "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
                "errorCode": error_code,
                "sourceEvidenceCurrent": False,
                "performanceBenchmarkReadinessSourceRefPresent": False,
                "benchmarkContextAvailable": False,
                "benchmarkReadinessDiagnostic": error_code,
                "sourceDiagnosticCodes": [error_code],
            },
        )
        _write_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"missing benchmark performance readiness proof error: {exc}", file=sys.stderr)
        return 2
    print(f"missing benchmark performance readiness proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate source-safe Lotus Performance benchmark-readiness proof for "
            "lotus-idea missing-benchmark review."
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


def _performance_summary(evidence: PerformanceBenchmarkReadinessEvidence) -> dict[str, object]:
    performance_ref = evidence.performance_ref
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-performance",
        "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
        "sourceEvidenceCurrent": (
            performance_ref is not None and performance_ref.freshness is EvidenceFreshness.CURRENT
        ),
        "performanceBenchmarkReadinessSourceRefPresent": performance_ref is not None,
        "benchmarkContextAvailable": evidence.benchmark_context_available,
        "benchmarkReadinessDiagnostic": evidence.performance_diagnostic or "",
        "sourceDiagnosticCodes": (
            [evidence.performance_diagnostic] if evidence.performance_diagnostic else []
        ),
    }


def _performance_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.performance_base_url or "").strip()
    if not base_url:
        raise ValueError(f"--performance-base-url or {PERFORMANCE_BASE_URL_ENV} is required")
    return base_url


def _timeout_seconds(args: argparse.Namespace) -> float:
    try:
        timeout = float(args.timeout_seconds)
    except ValueError as exc:
        raise ValueError("timeout seconds must be numeric") from exc
    if timeout <= 0:
        raise ValueError("timeout seconds must be positive")
    return timeout


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


def _write_payload(payload: dict[str, object], *, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        return
    print(rendered)


if __name__ == "__main__":
    sys.exit(main())
