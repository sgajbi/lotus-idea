from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys
from pathlib import Path

from app.application.missing_benchmark_live_proof import (
    build_missing_benchmark_live_proof_payload,
    core_source_ref_is_current,
)
from app.application.missing_benchmark_signal import (
    EvaluateMissingBenchmarkSignalCommand,
    evaluate_missing_benchmark_signal_command,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV = "LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_CORE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        as_of_date = _parse_date(args.as_of_date, "as-of-date")
        core_source = LotusCoreHighCashSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_core_control_plane_base_url(args),
                    timeout_seconds=_timeout_seconds(args),
                )
            )
        )
        evidence = core_source.fetch_benchmark_assignment_evidence(
            CoreBenchmarkAssignmentEvidenceRequest(
                portfolio_id=args.portfolio_id,
                as_of_date=as_of_date,
                reporting_currency=args.reporting_currency,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        proof_payload = build_missing_benchmark_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_core_source_attempted=True,
            evaluation_summary=_evaluation_summary(
                evidence=evidence,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
            ),
        )
        _write_payload(proof_payload, output=args.output)
        return 0
    except (
        CoreSourceEntitlementDenied,
        CoreSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"missing benchmark live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_missing_benchmark_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_core_source_attempted=True,
            evaluation_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-core",
                "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
                "errorCode": error_code,
                "evaluationOutcome": "blocked",
                "benchmarkAssignmentRefPresent": False,
                "benchmarkIdentityResolved": False,
                "assignmentEffectiveForAsOfDate": False,
                "assignmentStatus": "unknown",
                "assignmentVersionPresent": False,
                "sourceEvidenceCurrent": False,
                "sourceDiagnosticCodes": [error_code],
                "reasonCodes": ["source_partial"],
                "unsupportedReasons": ["source_unavailable"],
            },
        )
        _write_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"missing benchmark live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"missing benchmark live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Core missing-benchmark proof for lotus-idea."
    )
    parser.add_argument(
        "--core-query-control-plane-base-url",
        default=os.getenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV),
    )
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
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
    *,
    evidence: CoreBenchmarkAssignmentEvidence,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> dict[str, object]:
    result = evaluate_missing_benchmark_signal_command(
        EvaluateMissingBenchmarkSignalCommand(
            as_of_date=as_of_date,
            benchmark_assignment_ref=evidence.benchmark_assignment_ref,
            benchmark_identity_resolved=evidence.benchmark_identity_resolved,
            assignment_effective_for_as_of_date=evidence.assignment_effective_for_as_of_date,
            assignment_status=evidence.assignment_status,
            assignment_version_present=evidence.assignment_version_present,
            evaluated_at_utc=evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
        )
    )
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-core",
        "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
        "evaluationOutcome": result.outcome.value,
        "benchmarkAssignmentRefPresent": evidence.benchmark_assignment_ref is not None,
        "benchmarkIdentityResolved": evidence.benchmark_identity_resolved,
        "assignmentEffectiveForAsOfDate": evidence.assignment_effective_for_as_of_date,
        "assignmentStatus": evidence.assignment_status or "unknown",
        "assignmentVersionPresent": evidence.assignment_version_present,
        "sourceEvidenceCurrent": core_source_ref_is_current(evidence.benchmark_assignment_ref),
        "sourceDiagnosticCodes": (
            [evidence.assignment_diagnostic] if evidence.assignment_diagnostic else []
        ),
        "reasonCodes": [reason_code.value for reason_code in result.reason_codes],
        "unsupportedReasons": [reason.value for reason in result.unsupported_reasons],
    }


def _core_control_plane_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.core_query_control_plane_base_url or args.core_base_url or "").strip()
    if not base_url:
        raise ValueError(
            "--core-query-control-plane-base-url, --core-base-url, "
            f"{CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV}, or {CORE_BASE_URL_ENV} is required"
        )
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
    if isinstance(exc, CoreSourceEntitlementDenied):
        return "core_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "core_benchmark_assignment_source_unavailable"


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
