from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)

_AS_OF_DATE = date(2026, 6, 21)


def build_source_safe_runtime_trust_telemetry_repository(
    *,
    generated_at_utc: datetime,
) -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    result = evaluate_high_cash_signal(
        _high_cash_input(generated_at_utc=generated_at_utc),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    if result.outcome is not SignalEvaluationOutcome.CANDIDATE_CREATED or result.candidate is None:
        raise ValueError("runtime trust telemetry source-safe exercise did not create a candidate")
    repository.persist_candidate(
        result.candidate,
        idempotency_key="runtime-trust-telemetry-source-safe-exercise",
        payload={"runtimeTrustTelemetryExercise": "source-safe"},
        actor_subject="runtime-trust-telemetry-operator",
        occurred_at_utc=generated_at_utc,
    )
    return repository


def _high_cash_input(*, generated_at_utc: datetime) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=_AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref(
            "lotus-core:PortfolioStateSnapshot:v1", generated_at_utc=generated_at_utc
        ),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1", generated_at_utc=generated_at_utc),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1", generated_at_utc=generated_at_utc
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1", generated_at_utc=generated_at_utc
        ),
        evaluated_at_utc=generated_at_utc,
    )


def _source_ref(product_id: str, *, generated_at_utc: datetime) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="lotus-core://source-ref/redacted",
        as_of_date=_AS_OF_DATE,
        generated_at_utc=generated_at_utc,
        content_hash=f"sha256:runtime-trust-telemetry-source-safe-exercise:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
