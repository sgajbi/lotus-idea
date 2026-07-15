from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.high_volatility_runtime_evidence import (
    build_high_volatility_runtime_execution,
)
from app.application.high_volatility_signal import (
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    EvaluateHighVolatilityFromRiskCommand,
    evaluate_and_persist_high_volatility_signal_from_risk,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskVolatilityEvidence, RiskVolatilityEvidenceRequest

AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass(frozen=True)
class FixedRiskVolatilitySource:
    evidence: RiskVolatilityEvidence

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        return self.evidence


def runtime_command() -> EvaluateAndPersistHighVolatilityFromRiskCommand:
    return EvaluateAndPersistHighVolatilityFromRiskCommand(
        evaluation=EvaluateHighVolatilityFromRiskCommand(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=EVALUATED_AT,
        ),
        idempotency_key="high-volatility-runtime-evidence",
        actor_subject="runtime-evidence-test",
    )


def runtime_execution(
    *,
    repository: InMemoryIdeaRepository | None = None,
    durable_storage_backed: bool = True,
    evidence: RiskVolatilityEvidence | None = None,
    generated_at_utc: datetime = GENERATED_AT,
) -> dict[str, Any]:
    command = runtime_command()
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        command,
        risk_source=FixedRiskVolatilitySource(evidence or risk_evidence()),
        repository=repository or InMemoryIdeaRepository(),
    )
    return build_high_volatility_runtime_execution(
        generated_at_utc=generated_at_utc,
        command=command,
        result=result,
        durable_storage_backed=durable_storage_backed,
    )


def risk_evidence(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    as_of_date: date = AS_OF_DATE,
    source_system: SourceSystem = SourceSystem.LOTUS_RISK,
    volatility: Decimal = Decimal("14.25"),
) -> RiskVolatilityEvidence:
    return RiskVolatilityEvidence(
        source_reported_volatility=volatility,
        risk_supportability_state="ready",
        risk_ref=SourceRef(
            product_id="lotus-risk:RiskMetricsReport:v1",
            source_system=source_system,
            product_version="v1",
            route="/analytics/risk/metrics",
            as_of_date=as_of_date,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:risk-metrics-report",
            data_quality_status="ready",
            freshness=freshness,
        ),
        risk_diagnostic="risk_metrics_ready",
    )
