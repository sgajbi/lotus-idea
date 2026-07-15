from __future__ import annotations

from datetime import date, datetime

from app.application.core_benchmark_assignment_runtime_evidence import (
    EvaluateCoreBenchmarkAssignmentReadiness,
    build_core_benchmark_assignment_runtime_execution,
    evaluate_core_benchmark_assignment_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
)


class AuthoritativeCoreBenchmarkAssignmentSource:
    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        return CoreBenchmarkAssignmentEvidence(
            benchmark_assignment_ref=SourceRef(
                product_id="lotus-core:BenchmarkAssignment:v1",
                source_system=SourceSystem.LOTUS_CORE,
                product_version="v1",
                route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
                as_of_date=request.as_of_date,
                generated_at_utc=request.evaluated_at_utc,
                content_hash="sha256:test-benchmark-assignment",
                data_quality_status="complete",
                freshness=EvidenceFreshness.CURRENT,
            ),
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="active",
            assignment_version_present=True,
            assignment_diagnostic="core_benchmark_assignment_ready",
        )


def valid_core_benchmark_assignment_runtime_evidence(
    *, evaluated_at_utc: datetime, as_of_date: date | None = None
) -> dict[str, object]:
    command = EvaluateCoreBenchmarkAssignmentReadiness(
        tenant_id="test-tenant",
        portfolio_id="test-portfolio",
        as_of_date=as_of_date or evaluated_at_utc.date(),
        evaluated_at_utc=evaluated_at_utc,
        reporting_currency="USD",
    )
    result = evaluate_core_benchmark_assignment_readiness(
        command, core_source=AuthoritativeCoreBenchmarkAssignmentSource()
    )
    return build_core_benchmark_assignment_runtime_execution(
        generated_at_utc=evaluated_at_utc, result=result
    )
