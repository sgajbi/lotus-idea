from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import sys

from app.application.performance_underperformance_runtime_evidence import (
    build_performance_underperformance_runtime_execution,
    performance_underperformance_runtime_execution_is_valid,
)
from app.application.underperformance_signal import (
    EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    EvaluateUnderperformanceFromPerformanceCommand,
    evaluate_and_persist_underperformance_signal_from_performance,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.ports.performance_sources import (
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


class _Source:
    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        return PerformanceUnderperformanceEvidence(
            source_reported_active_return=Decimal("-0.018"),
            benchmark_context_available=True,
            performance_ref=SourceRef(
                product_id="lotus-performance:ReturnsSeriesBundle:v1",
                source_system=SourceSystem.LOTUS_PERFORMANCE,
                product_version="v1",
                route="/integration/returns/series",
                as_of_date=request.as_of_date,
                generated_at_utc=request.evaluated_at_utc,
                content_hash="sha256:performance-underperformance-contract-gate",
                data_quality_status="ready",
                freshness=EvidenceFreshness.CURRENT,
            ),
            performance_diagnostic="performance_benchmark_context_ready",
        )


def validate_performance_underperformance_runtime_execution_contract() -> list[str]:
    evaluated_at = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    command = EvaluateAndPersistUnderperformanceFromPerformanceCommand(
        evaluation=EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id="contract-gate-portfolio",
            as_of_date=date(2026, 6, 21),
            period_name="YTD",
            evaluated_at_utc=evaluated_at,
        ),
        idempotency_key="performance-underperformance-contract-gate",
        actor_subject="contract-gate",
    )
    result = evaluate_and_persist_underperformance_signal_from_performance(
        command,
        performance_source=_Source(),
        repository=InMemoryIdeaRepository(),
    )
    payload = build_performance_underperformance_runtime_execution(
        generated_at_utc=evaluated_at,
        command=command,
        result=result,
        durable_storage_backed=True,
    )
    errors: list[str] = []
    if not performance_underperformance_runtime_execution_is_valid(payload):
        errors.append(
            "valid performance underperformance runtime execution fixture should validate"
        )
    inflated = dict(payload)
    inflated["productionCertified"] = True
    if performance_underperformance_runtime_execution_is_valid(inflated):
        errors.append("performance underperformance runtime execution must reject unknown claims")
    return errors


def main() -> int:
    errors = validate_performance_underperformance_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Performance underperformance runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
