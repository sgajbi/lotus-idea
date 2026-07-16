from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.missing_benchmark_signal import (
    EvaluateMissingBenchmarkFromCoreCommand,
    EvaluateMissingBenchmarkSignalCommand,
    evaluate_missing_benchmark_readiness_from_core,
    evaluate_missing_benchmark_signal_command,
    evaluate_missing_benchmark_signal_from_core,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBenchmarkAssignmentSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubCoreBenchmarkAssignmentSource(CoreBenchmarkAssignmentSourcePort):
    def __init__(
        self,
        evidence: CoreBenchmarkAssignmentEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[CoreBenchmarkAssignmentEvidenceRequest] = []

    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_evaluate_missing_benchmark_signal_command_maps_source_input() -> None:
    result = evaluate_missing_benchmark_signal_command(
        EvaluateMissingBenchmarkSignalCommand(
            as_of_date=AS_OF_DATE,
            benchmark_assignment_ref=_source_ref(),
            benchmark_identity_resolved=False,
            assignment_effective_for_as_of_date=False,
            assignment_status="active",
            assignment_version_present=True,
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_missing_benchmark_")
    assert result.reason_codes == (ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED)


def test_evaluate_missing_benchmark_signal_from_core_uses_assignment_evidence() -> None:
    core_source = StubCoreBenchmarkAssignmentSource(
        CoreBenchmarkAssignmentEvidence(
            benchmark_assignment_ref=_source_ref(),
            benchmark_identity_resolved=False,
            assignment_effective_for_as_of_date=False,
            assignment_status="active",
            assignment_version_present=True,
            assignment_diagnostic="benchmark_identity_missing",
        )
    )

    result = evaluate_missing_benchmark_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.access_scope is not None
    assert result.candidate.access_scope.tenant_id == "tenant-a"
    assert result.reason_codes == (ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED)
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert core_source.requests[0].tenant_id == "tenant-a"
    assert core_source.requests[0].reporting_currency == "SGD"
    assert core_source.requests[0].correlation_id == "corr-core"


def test_readiness_use_case_preserves_authoritative_evidence_from_one_fetch() -> None:
    evidence = CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=_source_ref(),
        benchmark_identity_resolved=False,
        assignment_effective_for_as_of_date=False,
        assignment_status="active",
        assignment_version_present=True,
        assignment_diagnostic="core_benchmark_assignment_benchmark_identity_missing",
    )
    core_source = StubCoreBenchmarkAssignmentSource(evidence)

    result = evaluate_missing_benchmark_readiness_from_core(
        _command(),
        core_source=core_source,
    )

    assert result.evidence is evidence
    assert result.source_error_code is None
    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert len(core_source.requests) == 1


def test_evaluate_missing_benchmark_signal_from_core_ignores_ready_assignment() -> None:
    core_source = StubCoreBenchmarkAssignmentSource(
        CoreBenchmarkAssignmentEvidence(
            benchmark_assignment_ref=_source_ref(),
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="active",
            assignment_version_present=True,
            assignment_diagnostic="benchmark_assignment_ready",
        )
    )

    result = evaluate_missing_benchmark_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_evaluate_missing_benchmark_signal_from_core_blocks_entitlement_denial() -> None:
    result = evaluate_missing_benchmark_signal_from_core(
        _command(),
        core_source=StubCoreBenchmarkAssignmentSource(exception=CoreSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)

    preserved = evaluate_missing_benchmark_readiness_from_core(
        _command(),
        core_source=StubCoreBenchmarkAssignmentSource(exception=CoreSourceEntitlementDenied()),
    )
    assert preserved.evidence is None
    assert preserved.source_error_code == "core_source_entitlement_denied"


def test_evaluate_missing_benchmark_signal_from_core_blocks_source_unavailable() -> None:
    result = evaluate_missing_benchmark_signal_from_core(
        _command(),
        core_source=StubCoreBenchmarkAssignmentSource(
            exception=CoreSourceUnavailable(code="core_benchmark_assignment_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)

    preserved = evaluate_missing_benchmark_readiness_from_core(
        _command(),
        core_source=StubCoreBenchmarkAssignmentSource(
            exception=CoreSourceUnavailable(code="core_benchmark_assignment_pending")
        ),
    )
    assert preserved.evidence is None
    assert preserved.source_error_code == "core_benchmark_assignment_pending"


def _command() -> EvaluateMissingBenchmarkFromCoreCommand:
    return EvaluateMissingBenchmarkFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        reporting_currency="SGD",
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:BenchmarkAssignment:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:benchmark-assignment-gap",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
