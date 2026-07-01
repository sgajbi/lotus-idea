from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.bond_maturity_live_proof import (
    build_bond_maturity_live_proof_payload,
    core_maturity_source_refs_are_current,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


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
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        core_source = LotusCoreHighCashSourceAdapter(
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
        evidence = core_source.fetch_bond_maturity_evidence(
            CoreBondMaturityEvidenceRequest(
                portfolio_id=args.portfolio_id,
                as_of_date=_parse_date(args.as_of_date, "as-of-date"),
                evaluated_at_utc=evaluated_at_utc,
                maturity_window_days=args.maturity_window_days,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        proof_payload = build_bond_maturity_live_proof_payload(
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
        print(f"bond maturity live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_bond_maturity_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_core_source_attempted=True,
            evidence_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-core",
                "errorCode": error_code,
                "holdingsRefPresent": False,
                "maturityFactRefPresent": False,
                "nextMaturityDatePresent": False,
                "maturingPositionCountPresent": False,
                "sourceEvidenceCurrent": False,
                "maturityDiagnostic": error_code,
                "sourceDiagnosticCodes": [error_code],
            },
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"bond maturity live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"bond maturity live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Core maturity-summary proof."
    )
    parser.add_argument("--core-query-base-url", default=os.getenv(CORE_QUERY_BASE_URL_ENV))
    parser.add_argument("--core-base-url", default=os.getenv(CORE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--maturity-window-days", type=int, default=30)
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


def _evidence_summary(evidence: CoreBondMaturityEvidence) -> dict[str, object]:
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-core",
        "holdingsRefPresent": evidence.holdings_ref is not None,
        "maturityFactRefPresent": evidence.maturity_fact_ref is not None,
        "nextMaturityDatePresent": evidence.source_reported_next_maturity_date is not None,
        "maturingPositionCountPresent": (
            evidence.source_reported_maturing_position_count is not None
        ),
        "sourceEvidenceCurrent": core_maturity_source_refs_are_current(
            evidence.holdings_ref,
            evidence.maturity_fact_ref,
        ),
        "maturityDiagnostic": evidence.maturity_diagnostic or "unknown",
        "sourceDiagnosticCodes": (
            [evidence.maturity_diagnostic] if evidence.maturity_diagnostic else []
        ),
    }


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
    return str(code).strip() or "core_maturity_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
