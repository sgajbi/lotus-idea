from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Protocol

from app.application.source_runtime_evidence import sha256_json
from app.domain import EvidenceFreshness, SourceRef, SourceSystem


class PerformanceEvaluationRequest(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def as_of_date(self) -> date: ...

    @property
    def period_name(self) -> str: ...

    @property
    def evaluated_at_utc(self) -> datetime: ...


class PerformancePersistenceRequest(Protocol):
    @property
    def evaluation(self) -> PerformanceEvaluationRequest: ...

    @property
    def idempotency_key(self) -> str: ...

    @property
    def actor_subject(self) -> str: ...


def build_performance_runtime_command_fingerprint(
    command: PerformancePersistenceRequest,
) -> str:
    request = command.evaluation
    return sha256_json(
        {
            "portfolioId": request.portfolio_id,
            "asOfDate": request.as_of_date.isoformat(),
            "periodName": request.period_name,
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "idempotencyKey": command.idempotency_key,
            "actorSubject": command.actor_subject,
        }
    )


def source_ref_matches_performance_request(
    source_ref: SourceRef,
    *,
    product_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> bool:
    return bool(
        source_ref.product_id == product_id
        and source_ref.source_system is SourceSystem.LOTUS_PERFORMANCE
        and source_ref.as_of_date == as_of_date
        and source_ref.generated_at_utc <= evaluated_at_utc
        and source_ref.freshness is EvidenceFreshness.CURRENT
    )


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
