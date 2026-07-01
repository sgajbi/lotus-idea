from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.low_income_core_cashflow_live_proof import (
    build_low_income_core_cashflow_live_proof_payload,
    core_cashflow_source_refs_are_current,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import timeout_seconds_from_args, write_json_payload  # type: ignore[import-not-found,no-redef]

CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
CORE_QUERY_BASE_URL_ENV = "LOTUS_CORE_QUERY_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_CORE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        core_source = LotusCoreHighCashSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_core_query_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        evidence = core_source.fetch_low_income_evidence(
            CoreLowIncomeEvidenceRequest(
                portfolio_id=args.portfolio_id,
                as_of_date=_parse_date(args.as_of_date, "as-of-date"),
                evaluated_at_utc=evaluated_at_utc,
                horizon_days=args.horizon_days,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        proof_payload = build_low_income_core_cashflow_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_core_source_attempted=True,
            evidence_summary=_evidence_summary(evidence),
        )
        write_json_payload(proof_payload, output=args.output)
        return 0
    except (
        CoreSourceEntitlementDenied,
        CoreSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"low-income Core cashflow live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_low_income_core_cashflow_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_core_source_attempted=True,
            evidence_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-core",
                "errorCode": error_code,
                "cashMovementRefPresent": False,
                "cashflowProjectionRefPresent": False,
                "cashMovementCountPresent": False,
                "projectedCumulativeCashflowPresent": False,
                "sourceEvidenceCurrent": False,
                "cashflowDiagnostic": error_code,
                "sourceDiagnosticCodes": [error_code],
            },
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"low-income Core cashflow live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"low-income Core cashflow live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Core cashflow proof for low-income review."
    )
    parser.add_argument("--core-query-base-url", default=os.getenv(CORE_QUERY_BASE_URL_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--horizon-days", type=int, default=30)
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


def _evidence_summary(evidence: CoreLowIncomeEvidence) -> dict[str, object]:
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-core",
        "cashMovementRefPresent": evidence.cash_movement_ref is not None,
        "cashflowProjectionRefPresent": evidence.cashflow_projection_ref is not None,
        "cashMovementCountPresent": evidence.cash_movement_count is not None,
        "projectedCumulativeCashflowPresent": (
            evidence.source_reported_min_projected_cumulative_cashflow is not None
        ),
        "sourceEvidenceCurrent": core_cashflow_source_refs_are_current(
            evidence.cash_movement_ref,
            evidence.cashflow_projection_ref,
        ),
        "cashflowDiagnostic": evidence.cashflow_diagnostic or "unknown",
        "sourceDiagnosticCodes": (
            [evidence.cashflow_diagnostic] if evidence.cashflow_diagnostic else []
        ),
    }


def _core_query_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.core_query_base_url or args.core_base_url or "").strip()
    if not base_url:
        raise ValueError(
            "--core-query-base-url, --core-base-url, "
            f"{CORE_QUERY_BASE_URL_ENV}, or {CORE_BASE_URL_ENV} is required"
        )
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
    if isinstance(exc, CoreSourceEntitlementDenied):
        return "core_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "core_cashflow_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
