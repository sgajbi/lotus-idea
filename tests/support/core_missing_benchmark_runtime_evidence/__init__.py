from __future__ import annotations

from dataclasses import replace
from typing import Callable

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreSourceUnavailable,
)


class AuthoritativeCoreMissingBenchmarkSource:
    def __init__(
        self,
        *,
        evidence: CoreBenchmarkAssignmentEvidence | None = None,
        evidence_mutation: Callable[
            [CoreBenchmarkAssignmentEvidence], CoreBenchmarkAssignmentEvidence
        ]
        | None = None,
        error: CoreSourceUnavailable | None = None,
    ) -> None:
        self.evidence = evidence
        self.evidence_mutation = evidence_mutation
        self.error = error
        self.requests: list[CoreBenchmarkAssignmentEvidenceRequest] = []

    def close(self) -> None:
        pass

    def fetch_benchmark_assignment_evidence(
        self,
        request: CoreBenchmarkAssignmentEvidenceRequest,
    ) -> CoreBenchmarkAssignmentEvidence:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        evidence = self.evidence or missing_benchmark_evidence(request)
        return self.evidence_mutation(evidence) if self.evidence_mutation else evidence


def missing_benchmark_evidence(
    request: CoreBenchmarkAssignmentEvidenceRequest,
) -> CoreBenchmarkAssignmentEvidence:
    return CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=SourceRef(
            product_id="lotus-core:BenchmarkAssignment:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
            as_of_date=request.as_of_date,
            generated_at_utc=request.evaluated_at_utc,
            content_hash="sha256:" + "a" * 64,
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        ),
        benchmark_identity_resolved=False,
        assignment_effective_for_as_of_date=False,
        assignment_status="active",
        assignment_version_present=True,
        assignment_diagnostic="core_benchmark_assignment_benchmark_identity_missing",
    )


def ready_benchmark_evidence(
    request: CoreBenchmarkAssignmentEvidenceRequest,
) -> CoreBenchmarkAssignmentEvidence:
    return replace(
        missing_benchmark_evidence(request),
        benchmark_identity_resolved=True,
        assignment_effective_for_as_of_date=True,
        assignment_diagnostic="core_benchmark_assignment_ready",
    )
