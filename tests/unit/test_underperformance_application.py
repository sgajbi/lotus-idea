from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.underperformance_signal import (
    EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    EvaluateUnderperformanceFromPerformanceCommand,
    evaluate_and_persist_underperformance_signal_from_performance,
    evaluate_underperformance_signal_from_performance,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.ports.performance_sources import (
    PerformanceSourceEntitlementDenied,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubPerformanceSource:
    def __init__(
        self,
        evidence: PerformanceUnderperformanceEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[PerformanceUnderperformanceEvidenceRequest] = []

    def fetch_underperformance_evidence(
        self,
        request: PerformanceUnderperformanceEvidenceRequest,
    ) -> PerformanceUnderperformanceEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_underperformance_application_consumes_performance_source_evidence() -> None:
    performance_source = StubPerformanceSource(
        PerformanceUnderperformanceEvidence(
            source_reported_active_return=Decimal("-0.0125"),
            benchmark_context_available=True,
            performance_ref=_source_ref(),
            performance_diagnostic="performance_benchmark_context_ready",
        )
    )

    result = evaluate_underperformance_signal_from_performance(
        _command(),
        performance_source=performance_source,
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.reason_codes == (
        ReasonCode.UNDERPERFORMANCE_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )
    assert performance_source.requests[0].active_return_threshold == Decimal("-0.005")
    assert performance_source.requests[0].period_name == "YTD"


def test_underperformance_application_blocks_when_performance_source_unavailable() -> None:
    result = evaluate_underperformance_signal_from_performance(
        _command(),
        performance_source=StubPerformanceSource(
            exception=PerformanceSourceUnavailable(code="performance_returns_series_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_underperformance_application_blocks_entitlement_denial_without_candidate() -> None:
    result = evaluate_underperformance_signal_from_performance(
        _command(),
        performance_source=StubPerformanceSource(exception=PerformanceSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_underperformance_application_persists_candidate_and_replays_idempotently() -> None:
    repository = InMemoryIdeaRepository()
    source = StubPerformanceSource(
        PerformanceUnderperformanceEvidence(
            source_reported_active_return=Decimal("-0.0125"),
            benchmark_context_available=True,
            performance_ref=_source_ref(),
            performance_diagnostic="performance_benchmark_context_ready",
        )
    )
    command = EvaluateAndPersistUnderperformanceFromPerformanceCommand(
        evaluation=_command(),
        idempotency_key="performance-underperformance-runtime-proof",
        actor_subject="lotus-idea-runtime-proof",
    )

    accepted = evaluate_and_persist_underperformance_signal_from_performance(
        command,
        performance_source=source,
        repository=repository,
    )
    replayed = evaluate_and_persist_underperformance_signal_from_performance(
        command,
        performance_source=source,
        repository=repository,
    )

    assert accepted.persistence is not None
    assert accepted.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert accepted.source_diagnostic_codes == ("performance_benchmark_context_ready",)
    assert len(repository.snapshot().candidate_records) == 1
    assert len(repository.snapshot().idempotency_records) == 1


def test_underperformance_application_does_not_persist_non_candidate() -> None:
    result = evaluate_and_persist_underperformance_signal_from_performance(
        EvaluateAndPersistUnderperformanceFromPerformanceCommand(
            evaluation=_command(),
            idempotency_key="performance-underperformance-non-candidate",
            actor_subject="lotus-idea-runtime-proof",
        ),
        performance_source=StubPerformanceSource(
            PerformanceUnderperformanceEvidence(
                source_reported_active_return=Decimal("-0.001"),
                benchmark_context_available=True,
                performance_ref=_source_ref(),
            )
        ),
        repository=InMemoryIdeaRepository(),
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.persistence is None


@pytest.mark.parametrize(("field", "value"), (("idempotency_key", ""), ("actor_subject", " ")))
def test_underperformance_persistence_requires_operational_identity(
    field: str,
    value: str,
) -> None:
    command = EvaluateAndPersistUnderperformanceFromPerformanceCommand(
        evaluation=_command(),
        idempotency_key="performance-underperformance-runtime-proof",
        actor_subject="lotus-idea-runtime-proof",
    )

    with pytest.raises(ValueError, match=field):
        evaluate_and_persist_underperformance_signal_from_performance(
            replace(command, **{field: value}),
            performance_source=StubPerformanceSource(),
            repository=InMemoryIdeaRepository(),
        )


def _command() -> EvaluateUnderperformanceFromPerformanceCommand:
    return EvaluateUnderperformanceFromPerformanceCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=EVALUATED_AT,
        reporting_currency="USD",
        correlation_id="corr-performance",
        trace_id="trace-performance",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-performance:ReturnsSeriesBundle:v1",
        source_system=SourceSystem.LOTUS_PERFORMANCE,
        product_version="v1",
        route="/integration/returns/series",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:returns-series-bundle",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
