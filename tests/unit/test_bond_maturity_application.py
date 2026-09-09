from __future__ import annotations

from tests.support.evidence_digest import evidence_digest

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from app.application.bond_maturity_signal import (
    EvaluateAndPersistBondMaturityFromCoreCommand,
    EvaluateBondMaturityFromCoreCommand,
    EvaluateBondMaturitySignalCommand,
    evaluate_and_persist_bond_maturity_signal_from_core,
    evaluate_bond_maturity_signal_command,
    evaluate_bond_maturity_signal_from_core,
)
from app.application.candidate_expiry import CandidateExpiryDecision
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
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
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


class StubCoreBondMaturitySource(CoreBondMaturitySourcePort):
    def __init__(
        self,
        evidence: CoreBondMaturityEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[CoreBondMaturityEvidenceRequest] = []

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_evaluate_bond_maturity_signal_command_maps_source_input() -> None:
    result = evaluate_bond_maturity_signal_command(
        EvaluateBondMaturitySignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_next_maturity_date=date(2026, 7, 10),
            source_reported_maturing_position_count=2,
            holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
            maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_bond_maturity_")


def test_evaluate_bond_maturity_signal_from_core_uses_source_evidence() -> None:
    core_source = StubCoreBondMaturitySource(
        CoreBondMaturityEvidence(
            source_reported_next_maturity_date=date(2026, 7, 10),
            source_reported_maturing_position_count=2,
            holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
            maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
            maturity_diagnostic="core_maturity_evidence_ready",
        )
    )

    result = evaluate_bond_maturity_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED)
    assert result.candidate is not None
    assert result.candidate.access_scope is not None
    assert result.candidate.access_scope.tenant_id == "tenant-a"
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert core_source.requests[0].tenant_id == "tenant-a"
    assert core_source.requests[0].maturity_window_days == 30
    assert core_source.requests[0].correlation_id == "corr-core"


def test_evaluate_bond_maturity_signal_from_core_preserves_empty_window() -> None:
    core_source = StubCoreBondMaturitySource(
        CoreBondMaturityEvidence(
            source_reported_next_maturity_date=None,
            source_reported_maturing_position_count=0,
            holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
            maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
            maturity_diagnostic="core_maturity_window_empty",
        )
    )

    result = evaluate_bond_maturity_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_evaluate_bond_maturity_signal_from_core_blocks_entitlement_denial() -> None:
    result = evaluate_bond_maturity_signal_from_core(
        _command(),
        core_source=StubCoreBondMaturitySource(exception=CoreSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_evaluate_bond_maturity_signal_from_core_blocks_source_unavailable() -> None:
    result = evaluate_bond_maturity_signal_from_core(
        _command(),
        core_source=StubCoreBondMaturitySource(
            exception=CoreSourceUnavailable(code="core_maturity_contract_missing")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_persist_core_bond_maturity_candidate_and_exact_replay() -> None:
    source = StubCoreBondMaturitySource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()
    command = _persist_command()

    accepted = evaluate_and_persist_bond_maturity_signal_from_core(
        command,
        core_source=source,
        repository=repository,
    )
    replayed = evaluate_and_persist_bond_maturity_signal_from_core(
        command,
        core_source=source,
        repository=repository,
    )

    assert accepted.persistence is not None
    assert accepted.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert accepted.persistence.record is not None
    assert accepted.persistence.record.candidate.access_scope == ACCESS_SCOPE
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert len(repository.snapshot().candidate_records) == 1
    assert len(repository.snapshot().idempotency_records) == 1
    assert len(source.requests) == 2


def test_persist_core_bond_maturity_refuses_placeholder_scope_before_source_io() -> None:
    source = StubCoreBondMaturitySource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()

    with pytest.raises(UnscopedCandidatePersistenceError, match="must be authoritative"):
        evaluate_and_persist_bond_maturity_signal_from_core(
            replace(_persist_command(), access_scope=replace(ACCESS_SCOPE, client_id="unknown")),
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
def test_persist_core_bond_maturity_refuses_conflicting_scope_before_source_io(
    scope: ReviewAccessScope,
    message: str,
) -> None:
    source = StubCoreBondMaturitySource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()

    with pytest.raises(ValueError, match=message):
        evaluate_and_persist_bond_maturity_signal_from_core(
            replace(_persist_command(), access_scope=scope),
            core_source=source,
            repository=repository,
        )

    assert source.requests == []
    assert repository.snapshot().candidate_records == {}


@pytest.mark.parametrize(
    "exception",
    (CoreSourceEntitlementDenied(), CoreSourceUnavailable(code="core_maturity_unavailable")),
)
def test_persist_core_bond_maturity_source_refusal_creates_no_durable_state(
    exception: Exception,
) -> None:
    source = StubCoreBondMaturitySource(exception=exception)
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_bond_maturity_signal_from_core(
        _persist_command(),
        core_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert repository.snapshot().candidate_records == {}
    assert repository.snapshot().idempotency_records == {}
    assert repository.snapshot().outbox_events == {}


def test_persist_core_bond_maturity_expires_condition_no_longer_eligible() -> None:
    source = StubCoreBondMaturitySource(evidence=_eligible_evidence())
    repository = InMemoryIdeaRepository()
    created = evaluate_and_persist_bond_maturity_signal_from_core(
        _persist_command(),
        core_source=source,
        repository=repository,
    )
    assert created.persistence is not None and created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    source.evidence = CoreBondMaturityEvidence(
        source_reported_next_maturity_date=None,
        source_reported_maturing_position_count=0,
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
        maturity_diagnostic="core_maturity_window_empty",
    )

    expired = evaluate_and_persist_bond_maturity_signal_from_core(
        replace(
            _persist_command(),
            evaluation=replace(_command(), evaluated_at_utc=EVALUATED_AT + timedelta(hours=1)),
            idempotency_key="bond-maturity:not-eligible",
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


def _command() -> EvaluateBondMaturityFromCoreCommand:
    return EvaluateBondMaturityFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        maturity_window_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _persist_command() -> EvaluateAndPersistBondMaturityFromCoreCommand:
    return EvaluateAndPersistBondMaturityFromCoreCommand(
        evaluation=_command(),
        access_scope=ACCESS_SCOPE,
        idempotency_key="bond-maturity:tenant-a:PB_SG_GLOBAL_BAL_001:2026-06-21:30d",
        actor_subject="signal-ingestion-worker",
        accepted_at_utc=EVALUATED_AT,
    )


def _eligible_evidence() -> CoreBondMaturityEvidence:
    return CoreBondMaturityEvidence(
        source_reported_next_maturity_date=date(2026, 7, 10),
        source_reported_maturing_position_count=2,
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
        maturity_diagnostic="core_maturity_evidence_ready",
    )


def _source_ref(product_id: str, *, suffix: str = "") -> SourceRef:
    route_by_product = {
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/positions",
        "lotus-core:PortfolioMaturitySummary:v1": "/portfolios/{portfolio_id}/maturity-summary",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=evidence_digest(product_id, suffix),
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
