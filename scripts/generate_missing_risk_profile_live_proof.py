from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys

from app.application.missing_risk_profile_live_proof import (
    build_missing_risk_profile_live_proof_payload,
)
from app.application.missing_risk_profile_signal import (
    EvaluateMissingRiskProfileFromAdviseCommand,
    evaluate_missing_risk_profile_signal_from_advise,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_advise_sources import LotusAdvisePolicyEvaluationSourceAdapter
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


try:
    from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload
except ModuleNotFoundError:
    from proof_generator_io import timeout_seconds_from_args, write_json_payload  # type: ignore[import-not-found,no-redef]

ADVISE_BASE_URL_ENV = "LOTUS_ADVISE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_ADVISE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        advise_source = LotusAdvisePolicyEvaluationSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_advise_base_url(args),
                    timeout_seconds=timeout_seconds_from_args(args),
                )
            )
        )
        as_of_date = _parse_date(args.as_of_date, "as-of-date")
        evidence = advise_source.fetch_policy_evaluation_evidence(
            _request(
                evaluation_id=args.evaluation_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        evaluation = evaluate_missing_risk_profile_signal_from_advise(
            EvaluateMissingRiskProfileFromAdviseCommand(
                evaluation_id=args.evaluation_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            ),
            advise_source=_StaticAdviseSource(evidence),
        )
        proof_payload = build_missing_risk_profile_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_advise_source_attempted=True,
            evaluation_summary=_evaluation_summary(evaluation, evidence=evidence),
        )
        write_json_payload(proof_payload, output=args.output)
        return 0
    except (
        AdviseSourceEntitlementDenied,
        AdviseSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (
        DownstreamClientConfigurationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"missing risk-profile live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _request(
    *,
    evaluation_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    correlation_id: str | None,
    trace_id: str | None,
) -> AdvisePolicyEvaluationEvidenceRequest:
    return AdvisePolicyEvaluationEvidenceRequest(
        evaluation_id=evaluation_id,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


class _StaticAdviseSource:
    def __init__(self, evidence: AdvisePolicyEvaluationEvidence) -> None:
        self._evidence = evidence

    def fetch_policy_evaluation_evidence(self, _request: object) -> AdvisePolicyEvaluationEvidence:
        return self._evidence


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_missing_risk_profile_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_advise_source_attempted=True,
            evaluation_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-advise",
                "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                "errorCode": error_code,
                "sourceDiagnosticCodes": [error_code],
                "reasonCodes": [],
                "unsupportedReasons": ["source_unavailable"],
                "sourceEvidenceCurrent": False,
                "evaluationOutcome": "blocked",
            },
        )
        write_json_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"missing risk-profile live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"missing risk-profile live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Lotus Advise missing risk-profile proof."
    )
    parser.add_argument("--advise-base-url", default=os.getenv(ADVISE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware proof instant, for example 2026-06-28T10:10:00Z.",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        required=True,
        help="Timezone-aware evaluation instant, for example 2026-06-28T10:10:00Z.",
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
    evidence: AdvisePolicyEvaluationEvidence,
) -> dict[str, object]:
    source_refs = (
        evaluation.candidate.evidence_packet.source_refs if evaluation.candidate is not None else ()
    )
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-advise",
        "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        "evaluationOutcome": evaluation.outcome.value,
        "sourceEvidenceCurrent": any(
            source_ref.freshness is EvidenceFreshness.CURRENT for source_ref in source_refs
        ),
        "reasonCodes": [reason_code.value for reason_code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "sourceDiagnosticCodes": (
            [evidence.advise_diagnostic] if evidence.advise_diagnostic else []
        ),
    }


def _advise_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.advise_base_url or "").strip()
    if not base_url:
        raise ValueError(f"--advise-base-url or {ADVISE_BASE_URL_ENV} is required")
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
    if isinstance(exc, AdviseSourceEntitlementDenied):
        return "advise_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "advise_source_unavailable"


if __name__ == "__main__":
    sys.exit(main())
