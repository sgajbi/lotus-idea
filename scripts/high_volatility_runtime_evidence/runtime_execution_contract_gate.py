# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.high_volatility_runtime_evidence import (
    build_high_volatility_runtime_execution,
    high_volatility_runtime_execution_is_valid,
)
from app.application.high_volatility_signal import (
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    EvaluateHighVolatilityFromRiskCommand,
    evaluate_and_persist_high_volatility_signal_from_risk,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.risk_sources import RiskVolatilityEvidence, RiskVolatilityEvidenceRequest


class _Source:
    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        return RiskVolatilityEvidence(
            source_reported_volatility=Decimal("14.25"),
            risk_supportability_state="ready",
            risk_ref=SourceRef(
                product_id="lotus-risk:RiskMetricsReport:v1",
                source_system=SourceSystem.LOTUS_RISK,
                product_version="v1",
                route="/analytics/risk/metrics",
                as_of_date=request.as_of_date,
                generated_at_utc=request.evaluated_at_utc,
                content_hash="sha256:high-volatility-contract-gate",
                data_quality_status="ready",
                freshness=EvidenceFreshness.CURRENT,
            ),
            risk_diagnostic="risk_metrics_ready",
        )


def validate_high_volatility_runtime_execution_contract() -> list[str]:
    evaluated_at = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    command = EvaluateAndPersistHighVolatilityFromRiskCommand(
        evaluation=EvaluateHighVolatilityFromRiskCommand(
            portfolio_id="contract-gate-portfolio",
            as_of_date=date(2026, 6, 21),
            period_name="YTD",
            evaluated_at_utc=evaluated_at,
        ),
        idempotency_key="high-volatility-contract-gate",
        actor_subject="contract-gate",
    )
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        command,
        risk_source=_Source(),
        repository=InMemoryIdeaRepository(),
    )
    payload = build_high_volatility_runtime_execution(
        generated_at_utc=evaluated_at,
        command=command,
        result=result,
        durable_storage_backed=True,
    )
    errors: list[str] = []
    if not high_volatility_runtime_execution_is_valid(payload):
        errors.append("valid high-volatility runtime execution fixture should validate")
    inflated = dict(payload)
    inflated["productionCertified"] = True
    if high_volatility_runtime_execution_is_valid(inflated):
        errors.append("high-volatility runtime execution must reject unknown claim fields")
    return errors


def main() -> int:
    errors = validate_high_volatility_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("High-volatility runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
