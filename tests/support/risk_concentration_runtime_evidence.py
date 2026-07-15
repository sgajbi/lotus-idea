from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.concentration_risk_signal import (
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
    EvaluateConcentrationRiskFromRiskCommand,
    evaluate_and_persist_concentration_risk_signal_from_risk,
)
from app.application.risk_concentration_runtime_evidence import (
    build_risk_concentration_runtime_execution,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskConcentrationEvidence, RiskConcentrationEvidenceRequest

AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass(frozen=True)
class FixedRiskConcentrationSource:
    evidence: RiskConcentrationEvidence

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        return self.evidence


def runtime_command() -> EvaluateAndPersistConcentrationRiskFromRiskCommand:
    return EvaluateAndPersistConcentrationRiskFromRiskCommand(
        evaluation=EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=EVALUATED_AT,
        ),
        idempotency_key="risk-concentration-runtime-evidence",
        actor_subject="runtime-evidence-test",
    )


def runtime_execution(
    *,
    repository: InMemoryIdeaRepository | None = None,
    durable_storage_backed: bool = True,
    evidence: RiskConcentrationEvidence | None = None,
) -> dict[str, Any]:
    command = runtime_command()
    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        command,
        risk_source=FixedRiskConcentrationSource(evidence or risk_evidence()),
        repository=repository or InMemoryIdeaRepository(),
    )
    return build_risk_concentration_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=result,
        durable_storage_backed=durable_storage_backed,
    )


def risk_evidence(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    as_of_date: date = AS_OF_DATE,
    source_system: SourceSystem = SourceSystem.LOTUS_RISK,
) -> RiskConcentrationEvidence:
    return RiskConcentrationEvidence(
        top_position_weight_current=Decimal("0.22"),
        top_issuer_weight_current=Decimal("0.27"),
        issuer_coverage_status="complete",
        concentration_ref=SourceRef(
            product_id="lotus-risk:ConcentrationRiskReport:v1",
            source_system=source_system,
            product_version="v1",
            route="/analytics/risk/concentration",
            as_of_date=as_of_date,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:risk-concentration-report",
            data_quality_status="ready",
            freshness=freshness,
        ),
        concentration_diagnostic="risk_issuer_coverage_complete",
    )
