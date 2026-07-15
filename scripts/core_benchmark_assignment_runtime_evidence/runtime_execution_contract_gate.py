from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
import sys

from app.application.core_benchmark_assignment_runtime_evidence import (
    EvaluateCoreBenchmarkAssignmentReadiness,
    build_core_benchmark_assignment_runtime_execution,
    core_benchmark_assignment_runtime_execution_is_valid,
    evaluate_core_benchmark_assignment_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
)


class _CoreSource:
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
                content_hash="sha256:benchmark-assignment-contract-gate",
                data_quality_status="complete",
                freshness=EvidenceFreshness.CURRENT,
            ),
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="active",
            assignment_version_present=True,
            assignment_diagnostic="core_benchmark_assignment_ready",
        )


def validate_core_benchmark_assignment_runtime_execution_contract() -> list[str]:
    now = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    command = EvaluateCoreBenchmarkAssignmentReadiness(
        tenant_id="contract-gate-tenant",
        portfolio_id="contract-gate-portfolio",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=now,
        reporting_currency="USD",
    )
    result = evaluate_core_benchmark_assignment_readiness(command, core_source=_CoreSource())
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=now, result=result)
    errors: list[str] = []
    if not core_benchmark_assignment_runtime_execution_is_valid(payload):
        errors.append("authoritative Core benchmark-assignment runtime fixture must validate")
    tampered = deepcopy(payload)
    tampered["execution"]["sourceReceipt"]["contentHash"] = "sha256:tampered"
    if core_benchmark_assignment_runtime_execution_is_valid(tampered):
        errors.append("source receipt digest tampering must fail closed")
    inflated = deepcopy(payload)
    inflated["nonProofClaims"]["deploymentCertified"] = True
    if core_benchmark_assignment_runtime_execution_is_valid(inflated):
        errors.append("runtime evidence must reject deployment claim inflation")
    return errors


def main() -> int:
    errors = validate_core_benchmark_assignment_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Core benchmark-assignment runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
