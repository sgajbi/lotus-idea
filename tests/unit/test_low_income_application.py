from __future__ import annotations

from tests.support.evidence_digest import evidence_digest

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.candidate_expiry import CandidateExpiryDecision
from app.application.low_income_signal import (
    EvaluateAndPersistLowIncomeFromCoreCommand,
    EvaluateLowIncomeFromCoreCommand,
    EvaluateLowIncomeSignalCommand,
    evaluate_and_persist_low_income_signal_from_core,
    evaluate_low_income_signal_command,
    evaluate_low_income_signal_from_core,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    ReasonCode,
    ReviewAccessScope,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnscopedCandidatePersistenceError,
)
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
ACCESS_SCOPE = ReviewAccessScope(
    tenant_id="tenant-a",
    book_id="book-a",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-a",
)


class StubCoreLowIncomeSource(CoreLowIncomeSourcePort):
    def __init__(
        self,
        evidence: CoreLowIncomeEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[CoreLowIncomeEvidenceRequest] = []

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_evaluate_low_income_signal_command_maps_source_input() -> None:
    result = evaluate_low_income_signal_command(
        EvaluateLowIncomeSignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
            cash_movement_count=3,
            cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_low_income_")


def test_evaluate_low_income_signal_from_core_uses_source_evidence() -> None:
    core_source = StubCoreLowIncomeSource(
        CoreLowIncomeEvidence(
            source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
            cash_movement_count=3,
            cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
            cashflow_diagnostic="core_cashflow_liquidity_evidence_ready",
        )
    )

    result = evaluate_low_income_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.INCOME_ATTENTION, ReasonCode.REVIEW_REQUIRED)
    assert result.candidate is not None
    assert result.candidate.access_scope is not None
    assert result.candidate.access_scope.tenant_id == "tenant-a"
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert core_source.requests[0].tenant_id == "tenant-a"
    assert core_source.requests[0].horizon_days == 30
    assert core_source.requests[0].correlation_id == "corr-core"


def test_evaluate_low_income_signal_from_core_blocks_entitlement_denial() -> None:
    result = evaluate_low_income_signal_from_core(
        _command(),
        core_source=StubCoreLowIncomeSource(exception=CoreSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_evaluate_low_income_signal_from_core_blocks_source_unavailable() -> None:
    result = evaluate_low_income_signal_from_core(
        _command(),
        core_source=StubCoreLowIncomeSource(
            exception=CoreSourceUnavailable(code="core_cashflow_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_persist_core_cash_shortfall_candidate_and_exact_replay() -> None:
    source = StubCoreLowIncomeSource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()
    command = _persist_command()

    accepted = evaluate_and_persist_low_income_signal_from_core(
        command,
        core_source=source,
        repository=repository,
    )
    replayed = evaluate_and_persist_low_income_signal_from_core(
        command,
        core_source=source,
        repository=repository,
    )

    assert accepted.persistence is not None
    assert accepted.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert accepted.persistence.record is not None
    assert accepted.persistence.record.candidate.access_scope == ACCESS_SCOPE
    assert accepted.source_diagnostic_codes == ("core_cashflow_liquidity_evidence_ready",)
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert len(repository.snapshot().candidate_records) == 1
    assert len(repository.snapshot().idempotency_records) == 1
    assert len(repository.snapshot().outbox_events) == 1
    assert len(source.requests) == 2


def test_persist_core_cash_shortfall_requires_authoritative_scope_before_source_io() -> None:
    source = StubCoreLowIncomeSource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()

    with pytest.raises(UnscopedCandidatePersistenceError, match="must be authoritative"):
        evaluate_and_persist_low_income_signal_from_core(
            replace(_persist_command(), access_scope=replace(ACCESS_SCOPE, book_id="unknown")),
            core_source=source,
            repository=repository,
        )

    assert source.requests == []
    assert repository.snapshot().candidate_records == {}
    assert repository.snapshot().idempotency_records == {}
    assert repository.snapshot().outbox_events == {}


@pytest.mark.parametrize(
    ("scope", "message"),
    (
        (replace(ACCESS_SCOPE, tenant_id="tenant-b"), "tenant_id must match"),
        (replace(ACCESS_SCOPE, portfolio_id="portfolio-b"), "portfolio_id must match"),
    ),
)
def test_persist_core_cash_shortfall_rejects_conflicting_scope_before_source_io(
    scope: ReviewAccessScope,
    message: str,
) -> None:
    source = StubCoreLowIncomeSource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()

    with pytest.raises(ValueError, match=message):
        evaluate_and_persist_low_income_signal_from_core(
            replace(_persist_command(), access_scope=scope),
            core_source=source,
            repository=repository,
        )

    assert source.requests == []
    assert repository.snapshot().candidate_records == {}


@pytest.mark.parametrize(
    "exception",
    (CoreSourceEntitlementDenied(), CoreSourceUnavailable(code="core_cashflow_pending")),
)
def test_persist_core_cash_shortfall_source_refusal_creates_no_durable_state(
    exception: Exception,
) -> None:
    source = StubCoreLowIncomeSource(exception=exception)
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_low_income_signal_from_core(
        _persist_command(),
        core_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert result.expiry is None
    assert repository.snapshot().candidate_records == {}
    assert repository.snapshot().idempotency_records == {}
    assert repository.snapshot().outbox_events == {}


def test_persist_core_cash_shortfall_expires_authoritatively_resolved_condition() -> None:
    source = StubCoreLowIncomeSource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()
    created = evaluate_and_persist_low_income_signal_from_core(
        _persist_command(),
        core_source=source,
        repository=repository,
    )
    assert created.persistence is not None and created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    source.evidence = replace(
        _eligible_evidence(),
        source_reported_min_projected_cumulative_cashflow=Decimal("-5000"),
        cashflow_diagnostic="core_cashflow_above_shortfall_threshold",
    )

    expired = evaluate_and_persist_low_income_signal_from_core(
        replace(
            _persist_command(),
            evaluation=replace(_command(), evaluated_at_utc=EVALUATED_AT + timedelta(hours=1)),
            idempotency_key="low-income:resolved",
            accepted_at_utc=EVALUATED_AT + timedelta(hours=1),
        ),
        core_source=source,
        repository=repository,
    )

    assert expired.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert expired.persistence is None
    assert expired.expiry is not None
    assert expired.expiry.decision is CandidateExpiryDecision.EXPIRED
    assert (
        repository.snapshot().candidate_records[candidate_id].candidate.lifecycle_status
        is IdeaLifecycleStatus.EXPIRED
    )


@pytest.mark.parametrize("field_name", ("idempotency_key", "actor_subject"))
def test_persist_core_cash_shortfall_requires_non_blank_write_authority(field_name: str) -> None:
    source = StubCoreLowIncomeSource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()
    command = _persist_command()
    if field_name == "idempotency_key":
        command = replace(command, idempotency_key=" ")
    else:
        command = replace(command, actor_subject=" ")

    with pytest.raises(ValueError, match=f"{field_name} is required"):
        evaluate_and_persist_low_income_signal_from_core(
            command,
            core_source=source,
            repository=repository,
        )

    assert source.requests == []
    assert repository.snapshot().candidate_records == {}


def _command() -> EvaluateLowIncomeFromCoreCommand:
    return EvaluateLowIncomeFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        horizon_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _persist_command() -> EvaluateAndPersistLowIncomeFromCoreCommand:
    return EvaluateAndPersistLowIncomeFromCoreCommand(
        evaluation=_command(),
        access_scope=ACCESS_SCOPE,
        idempotency_key="low-income:tenant-a:PB_SG_GLOBAL_BAL_001:2026-06-21:30d",
        actor_subject="signal-ingestion-worker",
        accepted_at_utc=EVALUATED_AT,
    )


def _eligible_evidence() -> CoreLowIncomeEvidence:
    return CoreLowIncomeEvidence(
        source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
        cash_movement_count=3,
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        cashflow_diagnostic="core_cashflow_liquidity_evidence_ready",
    )


def _source_ref(product_id: str) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioCashMovementSummary:v1": (
            "/portfolios/{portfolio_id}/cash-movement-summary"
        ),
        "lotus-core:PortfolioCashflowProjection:v1": (
            "/portfolios/{portfolio_id}/cashflow-projection"
        ),
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=evidence_digest(product_id),
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
