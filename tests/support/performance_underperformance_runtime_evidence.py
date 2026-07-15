from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.application.performance_underperformance_runtime_evidence import (
    build_performance_underperformance_runtime_execution,
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

AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass(frozen=True)
class FixedPerformanceUnderperformanceSource:
    evidence: PerformanceUnderperformanceEvidence

    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        return self.evidence


def runtime_command() -> EvaluateAndPersistUnderperformanceFromPerformanceCommand:
    return EvaluateAndPersistUnderperformanceFromPerformanceCommand(
        evaluation=EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=EVALUATED_AT,
            reporting_currency="USD",
        ),
        idempotency_key="performance-underperformance-runtime-evidence",
        actor_subject="runtime-evidence-test",
    )


def runtime_execution(
    *,
    repository: InMemoryIdeaRepository | None = None,
    durable_storage_backed: bool = True,
    evidence: PerformanceUnderperformanceEvidence | None = None,
    generated_at_utc: datetime = GENERATED_AT,
) -> dict[str, Any]:
    command = runtime_command()
    result = evaluate_and_persist_underperformance_signal_from_performance(
        command,
        performance_source=FixedPerformanceUnderperformanceSource(
            evidence or performance_evidence()
        ),
        repository=repository or InMemoryIdeaRepository(),
    )
    return build_performance_underperformance_runtime_execution(
        generated_at_utc=generated_at_utc,
        command=command,
        result=result,
        durable_storage_backed=durable_storage_backed,
    )


def performance_evidence(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    as_of_date: date = AS_OF_DATE,
    source_system: SourceSystem = SourceSystem.LOTUS_PERFORMANCE,
    active_return: Decimal = Decimal("-0.018"),
    benchmark_context_available: bool = True,
) -> PerformanceUnderperformanceEvidence:
    return PerformanceUnderperformanceEvidence(
        source_reported_active_return=active_return,
        benchmark_context_available=benchmark_context_available,
        performance_ref=SourceRef(
            product_id="lotus-performance:ReturnsSeriesBundle:v1",
            source_system=source_system,
            product_version="v1",
            route="/integration/returns/series",
            as_of_date=as_of_date,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:performance-returns-series",
            data_quality_status="ready",
            freshness=freshness,
        ),
        performance_diagnostic="performance_benchmark_context_ready",
    )
