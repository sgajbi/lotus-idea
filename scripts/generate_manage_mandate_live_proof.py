from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import json
import os
import sys
from pathlib import Path

from app.application.manage_mandate_live_proof import build_manage_mandate_live_proof_payload
from app.application.mandate_health_signal import (
    EvaluateMandateHealthFromManageCommand,
    evaluate_mandate_health_signal_from_manage,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.infrastructure.lotus_manage_sources import LotusManageMandateHealthSourceAdapter
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceEntitlementDenied,
    ManageSourceUnavailable,
)


MANAGE_BASE_URL_ENV = "LOTUS_MANAGE_BASE_URL"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_MANAGE_TIMEOUT_SECONDS"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at_utc = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        as_of_date = _parse_date(args.as_of_date, "as-of-date")
        manage_source = LotusManageMandateHealthSourceAdapter(
            DownstreamJsonClient(
                DownstreamClientConfig(
                    base_url=_manage_base_url(args),
                    timeout_seconds=_timeout_seconds(args),
                )
            )
        )
        evidence = manage_source.fetch_mandate_health_evidence(
            _request(
                portfolio_id=args.portfolio_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            )
        )
        evaluation = evaluate_mandate_health_signal_from_manage(
            EvaluateMandateHealthFromManageCommand(
                portfolio_id=args.portfolio_id,
                as_of_date=as_of_date,
                evaluated_at_utc=evaluated_at_utc,
                correlation_id=args.correlation_id,
                trace_id=args.trace_id,
            ),
            manage_source=_StaticManageSource(evidence),
        )
        proof_payload = build_manage_mandate_live_proof_payload(
            generated_at_utc=generated_at_utc,
            live_manage_source_attempted=True,
            evaluation_summary=_evaluation_summary(evaluation, evidence=evidence),
        )
        _write_payload(proof_payload, output=args.output)
        return 0
    except (
        ManageSourceEntitlementDenied,
        ManageSourceUnavailable,
        DownstreamServiceError,
    ) as exc:
        return _write_blocked_source_proof(args=args, error_code=_source_error_code(exc))
    except (
        DownstreamClientConfigurationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"manage mandate live proof configuration error: {exc}", file=sys.stderr)
        return 2


def _request(
    *,
    portfolio_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    correlation_id: str | None,
    trace_id: str | None,
) -> ManageMandateHealthEvidenceRequest:
    return ManageMandateHealthEvidenceRequest(
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


class _StaticManageSource:
    def __init__(self, evidence: ManageMandateHealthEvidence) -> None:
        self._evidence = evidence

    def fetch_mandate_health_evidence(self, _request: object) -> ManageMandateHealthEvidence:
        return self._evidence


def _write_blocked_source_proof(*, args: argparse.Namespace, error_code: str) -> int:
    try:
        proof_payload = build_manage_mandate_live_proof_payload(
            generated_at_utc=_parse_instant(args.generated_at_utc, "generated-at-utc"),
            live_manage_source_attempted=True,
            evaluation_summary={
                "runStatus": "blocked",
                "sourceAuthority": "lotus-manage",
                "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
                "errorCode": error_code,
                "sourceDiagnosticCodes": [error_code],
                "reasonCodes": [],
                "unsupportedReasons": ["source_unavailable"],
                "sourceEvidenceCurrent": False,
                "portfolioScopeConfirmed": False,
                "manageActionRegisterReady": False,
                "workflowDecisionCount": 0,
                "lineageEdgeCount": 0,
            },
        )
        _write_payload(proof_payload, output=args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"manage mandate live proof error: {exc}", file=sys.stderr)
        return 2
    print(f"manage mandate live proof blocked: {error_code}", file=sys.stderr)
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe live Lotus Manage mandate proof."
    )
    parser.add_argument("--manage-base-url", default=os.getenv(MANAGE_BASE_URL_ENV))
    parser.add_argument("--timeout-seconds", default=os.getenv(TIMEOUT_SECONDS_ENV, "2.0"))
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware proof instant, for example 2026-06-27T10:10:00Z.",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        required=True,
        help="Timezone-aware evaluation instant, for example 2026-06-27T10:10:00Z.",
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
    evidence: ManageMandateHealthEvidence,
) -> dict[str, object]:
    source_refs = (
        evaluation.candidate.evidence_packet.source_refs if evaluation.candidate is not None else ()
    )
    return {
        "runStatus": "completed",
        "sourceAuthority": "lotus-manage",
        "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
        "evaluationOutcome": evaluation.outcome.value,
        "sourceEvidenceCurrent": any(
            source_ref.freshness is EvidenceFreshness.CURRENT for source_ref in source_refs
        ),
        "portfolioScopeConfirmed": evidence.portfolio_scope_confirmed,
        "manageActionRegisterReady": str(evidence.supportability_state or "").lower() == "ready",
        "workflowDecisionCount": evidence.workflow_decision_count or 0,
        "lineageEdgeCount": evidence.lineage_edge_count or 0,
        "reasonCodes": [reason_code.value for reason_code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "sourceDiagnosticCodes": (
            [evidence.manage_diagnostic] if evidence.manage_diagnostic else []
        ),
    }


def _manage_base_url(args: argparse.Namespace) -> str:
    base_url = str(args.manage_base_url or "").strip()
    if not base_url:
        raise ValueError(f"--manage-base-url or {MANAGE_BASE_URL_ENV} is required")
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
    if isinstance(exc, ManageSourceEntitlementDenied):
        return "manage_source_entitlement_denied"
    code = getattr(exc, "code", "")
    return str(code).strip() or "manage_source_unavailable"


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
