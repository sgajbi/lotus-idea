from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.drawdown_review_signal import (
    EvaluateAndPersistDrawdownReviewFromRiskCommand,
    EvaluateDrawdownReviewFromRiskCommand,
    evaluate_and_persist_drawdown_review_signal_from_risk,
)
from app.application.risk_drawdown_runtime_evidence import (
    build_risk_drawdown_runtime_execution,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskDrawdownEvidence, RiskDrawdownEvidenceRequest

AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass(frozen=True)
class FixedRiskDrawdownSource:
    evidence: RiskDrawdownEvidence

    def fetch_drawdown_evidence(
        self, request: RiskDrawdownEvidenceRequest
    ) -> RiskDrawdownEvidence:
        return self.evidence


def runtime_command() -> EvaluateAndPersistDrawdownReviewFromRiskCommand:
    return EvaluateAndPersistDrawdownReviewFromRiskCommand(
        evaluation=EvaluateDrawdownReviewFromRiskCommand(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=EVALUATED_AT,
        ),
        idempotency_key="risk-drawdown-runtime-evidence",
        actor_subject="runtime-evidence-test",
    )


def runtime_execution(
    *,
    repository: InMemoryIdeaRepository | None = None,
    durable_storage_backed: bool = True,
    evidence: RiskDrawdownEvidence | None = None,
    generated_at_utc: datetime = GENERATED_AT,
) -> dict[str, Any]:
    command = runtime_command()
    result = evaluate_and_persist_drawdown_review_signal_from_risk(
        command,
        risk_source=FixedRiskDrawdownSource(evidence or risk_evidence()),
        repository=repository or InMemoryIdeaRepository(),
    )
    return build_risk_drawdown_runtime_execution(
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
    max_drawdown: Decimal = Decimal("-0.1245"),
) -> RiskDrawdownEvidence:
    return RiskDrawdownEvidence(
        source_reported_max_drawdown=max_drawdown,
        risk_supportability_state="ready",
        risk_ref=SourceRef(
            product_id="lotus-risk:DrawdownAnalyticsReport:v1",
            source_system=source_system,
            product_version="v1",
            route="/analytics/risk/drawdown",
            as_of_date=as_of_date,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:drawdown-analytics-report",
            data_quality_status="ready",
            freshness=freshness,
        ),
        risk_diagnostic="risk_drawdown_source_ready",
    )
