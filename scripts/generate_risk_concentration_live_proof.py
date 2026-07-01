from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.concentration_risk_signal import (
    EvaluateConcentrationRiskSignalCommand,
    EvaluateConcentrationRiskFromRiskCommand,
    evaluate_concentration_risk_signal_command,
)
from app.application.risk_concentration_live_proof import (
    build_risk_concentration_live_proof_payload,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_risk_sources import LotusRiskConcentrationSourceAdapter
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import timeout_seconds_from_args, write_json_payload  # type: ignore[import-not-found,no-redef]

RISK_BASE_URL_ENV = "LOTUS_RISK_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_RISK_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        risk_source = LotusRiskConcentrationSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_risk_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        command = EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id=args.portfolio_id,
            as_of_date=_parse_date(args.as_of_date, "as-of-date"),
            evaluated_at_utc=evaluated_at_utc,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
        )
        evidence = risk_source.fetch_concentration_evidence(
            RiskConcentrationEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
        evaluation = evaluate_concentration_risk_signal_command(
            EvaluateConcentrationRiskSignalCommand(
                as_of_date=command.as_of_date,
                top_position_weight_current=evidence.top_position_weight_current,
                top_issuer_weight_current=evidence.top_issuer_weight_current,
                issuer_coverage_status=evidence.issuer_coverage_status,
                concentration_ref=evidence.concentration_ref,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=evidence.entitlement_allowed,
            )
        )
        proof_payload = build_risk_concentration_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_risk_source_attempted=True,
            evaluation_summary=_evaluation_summary(evaluation, evidence=evidence),
        )
        write_json_payload(proof_payload, output=args.output)
        return 0
    except (
        RiskSourceEntitlementDenied,
        RiskSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (DownstreamClientConfigurationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"risk concentration live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_risk_concentration_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_risk_source_attempted=True,
            evaluation_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-risk",
                "sourceProductId": "lotus-risk:ConcentrationRiskReport:v1",
                "errorCode": error_code,
                "sourceDiagnosticCodes": [error_code],
                "reasonCodes": [],
                "unsupportedReasons": ["source_unavailable"],
                "sourceEvidenceCurrent": False,
            },
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"risk concentration live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"risk concentration live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Lotus Risk concentration proof for lotus-idea."
    )
    parser.add_argument("--risk-base-url", default=os.getenv(RISK_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
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
    evidence: RiskConcentrationEvidence,
) -> dict[str, object]:
    source_refs = (
        evaluation.candidate.evidence_packet.source_refs if evaluation.candidate is not None else ()
    )
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-risk",
        "sourceProductId": "lotus-risk:ConcentrationRiskReport:v1",
        "evaluationOutcome": evaluation.outcome.value,
        "sourceEvidenceCurrent": any(
            source_ref.freshness is EvidenceFreshness.CURRENT for source_ref in source_refs
        ),
        "reasonCodes": [reason_code.value for reason_code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "sourceDiagnosticCodes": (
            [evidence.concentration_diagnostic] if evidence.concentration_diagnostic else []
        ),
    }


def _risk_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.risk_base_url or "").strip()
    if not base_url:
        raise ValueError(f"--risk-base-url or {RISK_BASE_URL_ENV} is required")
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
    if isinstance(exc, RiskSourceEntitlementDenied):
        return "risk_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "risk_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
