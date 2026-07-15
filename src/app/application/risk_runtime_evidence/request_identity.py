from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Protocol

from app.application.risk_runtime_evidence.receipts import sha256_json
from app.domain import OpportunityFamily, SignalEvaluationResult, SourceRef, SourceSystem
from app.ports.evidence_payloads import source_ref_payload


class RiskEvaluationRequest(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def as_of_date(self) -> date: ...

    @property
    def period_name(self) -> str: ...

    @property
    def evaluated_at_utc(self) -> datetime: ...


class RiskPersistenceRequest(Protocol):
    @property
    def evaluation(self) -> RiskEvaluationRequest: ...

    @property
    def idempotency_key(self) -> str: ...

    @property
    def actor_subject(self) -> str: ...


def build_risk_candidate_idempotency_payload(
    *,
    portfolio_id: str,
    as_of_date: date,
    period_name: str,
    evaluated_at_utc: datetime,
    family: OpportunityFamily,
    policy_version: str,
    evaluation: SignalEvaluationResult,
) -> dict[str, Any]:
    candidate = evaluation.candidate
    source_refs = candidate.evidence_packet.source_refs if candidate is not None else ()
    return {
        "as_of_date": as_of_date.isoformat(),
        "candidate_id": candidate.candidate_id if candidate is not None else None,
        "evaluated_at_utc": evaluated_at_utc.isoformat(),
        "family": family.value,
        "period_name": period_name,
        "portfolio_id": portfolio_id,
        "policy_version": policy_version,
        "source_signal_ids": list(candidate.source_signal_ids) if candidate is not None else [],
        "source_refs": [source_ref_payload(source_ref) for source_ref in source_refs],
    }


def build_risk_runtime_request_fingerprint(
    *,
    portfolio_id: str,
    as_of_date: date,
    period_name: str,
    evaluated_at_utc: datetime,
    idempotency_key: str,
    actor_subject: str,
) -> str:
    return sha256_json(
        {
            "portfolioId": portfolio_id,
            "asOfDate": as_of_date.isoformat(),
            "periodName": period_name,
            "evaluatedAtUtc": _format_utc(evaluated_at_utc),
            "idempotencyKey": idempotency_key,
            "actorSubject": actor_subject,
        }
    )


def build_risk_runtime_command_fingerprint(command: RiskPersistenceRequest) -> str:
    request = command.evaluation
    return build_risk_runtime_request_fingerprint(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date,
        period_name=request.period_name,
        evaluated_at_utc=request.evaluated_at_utc,
        idempotency_key=command.idempotency_key,
        actor_subject=command.actor_subject,
    )


def source_ref_matches_risk_request(
    source_ref: SourceRef,
    *,
    product_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> bool:
    return bool(
        source_ref.product_id == product_id
        and source_ref.source_system is SourceSystem.LOTUS_RISK
        and source_ref.as_of_date == as_of_date
        and source_ref.generated_at_utc <= evaluated_at_utc
        and source_ref.freshness.value == "current"
    )


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
