from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import sys

from app.application.drawdown_review_signal import (
    EvaluateAndPersistDrawdownReviewFromRiskCommand,
    EvaluateDrawdownReviewFromRiskCommand,
    evaluate_and_persist_drawdown_review_signal_from_risk,
)
from app.application.risk_drawdown_runtime_evidence import (
    build_risk_drawdown_runtime_execution,
    risk_drawdown_runtime_execution_is_valid,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskDrawdownEvidence, RiskDrawdownEvidenceRequest


class _Source:
    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        return RiskDrawdownEvidence(
            source_reported_max_drawdown=Decimal("-0.1245"),
            risk_supportability_state="ready",
            risk_ref=SourceRef(
                product_id="lotus-risk:DrawdownAnalyticsReport:v1",
                source_system=SourceSystem.LOTUS_RISK,
                product_version="v1",
                route="/analytics/risk/drawdown",
                as_of_date=request.as_of_date,
                generated_at_utc=request.evaluated_at_utc,
                content_hash="sha256:risk-drawdown-contract-gate",
                data_quality_status="ready",
                freshness=EvidenceFreshness.CURRENT,
            ),
            risk_diagnostic="risk_drawdown_source_ready",
        )


def validate_risk_drawdown_runtime_execution_contract() -> list[str]:
    evaluated_at = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    command = EvaluateAndPersistDrawdownReviewFromRiskCommand(
        evaluation=EvaluateDrawdownReviewFromRiskCommand(
            portfolio_id="contract-gate-portfolio",
            as_of_date=date(2026, 6, 21),
            period_name="YTD",
            evaluated_at_utc=evaluated_at,
        ),
        idempotency_key="risk-drawdown-contract-gate",
        actor_subject="contract-gate",
    )
    result = evaluate_and_persist_drawdown_review_signal_from_risk(
        command,
        risk_source=_Source(),
        repository=InMemoryIdeaRepository(),
    )
    payload = build_risk_drawdown_runtime_execution(
        generated_at_utc=evaluated_at,
        command=command,
        result=result,
        durable_storage_backed=True,
    )
    errors: list[str] = []
    if not risk_drawdown_runtime_execution_is_valid(payload):
        errors.append("valid risk drawdown runtime execution fixture should validate")
    inflated = dict(payload)
    inflated["productionCertified"] = True
    if risk_drawdown_runtime_execution_is_valid(inflated):
        errors.append("risk drawdown runtime execution must reject unknown claim fields")
    return errors


def main() -> int:
    errors = validate_risk_drawdown_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Risk drawdown runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
