from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import sys

from app.application.concentration_risk_signal import (
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
    EvaluateConcentrationRiskFromRiskCommand,
    evaluate_and_persist_concentration_risk_signal_from_risk,
)
from app.application.risk_concentration_runtime_evidence import (
    build_risk_concentration_runtime_execution,
    risk_concentration_runtime_execution_is_valid,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskConcentrationEvidence, RiskConcentrationEvidenceRequest


class _Source:
    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        return RiskConcentrationEvidence(
            top_position_weight_current=Decimal("0.22"),
            top_issuer_weight_current=Decimal("0.27"),
            issuer_coverage_status="complete",
            concentration_ref=SourceRef(
                product_id="lotus-risk:ConcentrationRiskReport:v1",
                source_system=SourceSystem.LOTUS_RISK,
                product_version="v1",
                route="/analytics/risk/concentration",
                as_of_date=request.as_of_date,
                generated_at_utc=request.evaluated_at_utc,
                content_hash="sha256:risk-concentration-contract-gate",
                data_quality_status="ready",
                freshness=EvidenceFreshness.CURRENT,
            ),
            concentration_diagnostic="risk_issuer_coverage_complete",
        )


def validate_risk_concentration_runtime_execution_contract() -> list[str]:
    evaluated_at = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    command = EvaluateAndPersistConcentrationRiskFromRiskCommand(
        evaluation=EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id="contract-gate-portfolio",
            as_of_date=date(2026, 6, 21),
            evaluated_at_utc=evaluated_at,
        ),
        idempotency_key="risk-concentration-contract-gate",
        actor_subject="contract-gate",
    )
    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        command,
        risk_source=_Source(),
        repository=InMemoryIdeaRepository(),
    )
    payload = build_risk_concentration_runtime_execution(
        generated_at_utc=evaluated_at,
        command=command,
        result=result,
        durable_storage_backed=True,
    )
    errors: list[str] = []
    if not risk_concentration_runtime_execution_is_valid(payload):
        errors.append("valid risk concentration runtime execution fixture should validate")
    inflated = dict(payload)
    inflated["productionCertified"] = True
    if risk_concentration_runtime_execution_is_valid(inflated):
        errors.append("risk concentration runtime execution must reject unknown claim fields")
    return errors


def main() -> int:
    errors = validate_risk_concentration_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Risk concentration runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
