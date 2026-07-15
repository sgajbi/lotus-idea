from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Protocol

from app.application.candidate_persistence_identity import build_candidate_idempotency_payload
from app.application.risk_runtime_evidence.receipts import sha256_json
from app.domain import OpportunityFamily, SignalEvaluationResult, SourceRef, SourceSystem


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
    return build_candidate_idempotency_payload(
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        period_name=period_name,
        evaluated_at_utc=evaluated_at_utc,
        family=family,
        policy_version=policy_version,
        evaluation=evaluation,
    )


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
