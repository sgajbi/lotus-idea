from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    CandidateChangeReason,
    CandidatePersistenceDecision,
    CandidatePersistenceResult,
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    ReviewAccessScope,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    evaluate_high_cash_signal,
)
from app.domain.opportunity_identity import (
    OPPORTUNITY_IDENTITY_POLICY_VERSION,
    PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION,
)


AS_OF_DATE = datetime(2026, 6, 21, 10, 0, tzinfo=UTC).date()
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

TERMINAL_STATE_EXPECTATIONS = (
    (IdeaLifecycleStatus.ACCEPTED, ReviewPosture.APPROVED_FOR_CONVERSION),
    (IdeaLifecycleStatus.REJECTED, ReviewPosture.REJECTED),
    (IdeaLifecycleStatus.EXPIRED, ReviewPosture.NO_ACTION),
    (IdeaLifecycleStatus.EXECUTED, ReviewPosture.APPROVED_FOR_CONVERSION),
    (IdeaLifecycleStatus.CLOSED, ReviewPosture.NO_ACTION),
)


def _source_ref(
    product_id: str,
    *,
    content_hash: str | None = None,
    as_of_date: date = AS_OF_DATE,
    evaluated_at_utc: datetime = EVALUATED_AT,
) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolio_id}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/cash-balances",
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
        as_of_date=as_of_date,
        generated_at_utc=evaluated_at_utc,
        content_hash=content_hash or f"sha256:{product_id}:{as_of_date.isoformat()}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _candidate(
    *,
    cash_weight: Decimal = Decimal("0.18"),
    cashflow_hash: str | None = None,
    as_of_date: date = AS_OF_DATE,
    evaluated_at_utc: datetime = EVALUATED_AT,
) -> tuple[IdeaCandidate, tuple[SourceRef, ...]]:
    refs = (
        _source_ref(
            "lotus-core:PortfolioStateSnapshot:v1",
            as_of_date=as_of_date,
            evaluated_at_utc=evaluated_at_utc,
        ),
        _source_ref(
            "lotus-core:HoldingsAsOf:v1",
            as_of_date=as_of_date,
            evaluated_at_utc=evaluated_at_utc,
        ),
        _source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            as_of_date=as_of_date,
            evaluated_at_utc=evaluated_at_utc,
        ),
        _source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            content_hash=cashflow_hash,
            as_of_date=as_of_date,
            evaluated_at_utc=evaluated_at_utc,
        ),
    )
    evaluation = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=as_of_date,
            source_reported_cash_weight=cash_weight,
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=evaluated_at_utc,
            access_scope=ReviewAccessScope(
                tenant_id="tenant-sg-001",
                book_id="book-private-bank-sg",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                client_id="client-001",
            ),
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v2",
            cash_weight_threshold=Decimal("0.12"),
        ),
    )
    assert evaluation.candidate is not None
    return evaluation.candidate, refs


def _persist(
    repository: InMemoryIdeaRepository,
    candidate: IdeaCandidate,
    refs: tuple[SourceRef, ...],
    *,
    sequence: int,
    occurred_at_utc: datetime = EVALUATED_AT,
) -> CandidatePersistenceResult:
    return repository.persist_candidate(
        candidate,
        idempotency_key=f"signal-ingestion:high-cash:{sequence:03d}",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=occurred_at_utc,
    )


def test_evidence_correction_preserves_review_state_and_versions_evidence() -> None:
    candidate, refs = _candidate()
    reviewed_candidate = replace(
        candidate,
        lifecycle_status=IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
        review_posture=ReviewPosture.ADVISOR_REVIEWED,
    )
    corrected_candidate, corrected_refs = _candidate(cashflow_hash="sha256:corrected-cashflow")
    repository = InMemoryIdeaRepository()
    _persist(repository, reviewed_candidate, refs, sequence=1)

    corrected = _persist(
        repository,
        corrected_candidate,
        corrected_refs,
        sequence=2,
        occurred_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
    )

    assert corrected.decision is CandidatePersistenceDecision.EVIDENCE_REFRESHED
    assert corrected.record is not None
    assert corrected.record.candidate.candidate_id == candidate.candidate_id
    assert corrected.record.candidate.lifecycle_status is IdeaLifecycleStatus.REVIEWED_BY_ADVISOR
    assert corrected.record.candidate.review_posture is ReviewPosture.ADVISOR_REVIEWED
    assert corrected.record.candidate.identity.material_version == 1
    assert corrected.record.candidate.identity.evidence_version == 2
    assert (
        corrected.record.candidate.identity.change_reason
        is CandidateChangeReason.EVIDENCE_CORRECTION
    )
    assert len(corrected.record.version_history) == 2
    assert corrected.record.audit_events[-1].event_type == "idea.candidate.evidence_refreshed"
    assert tuple(repository.snapshot().outbox_events.values())[-1].event_type == (
        "idea.candidate.evidence_refreshed.v1"
    )


def test_material_change_creates_version_and_clears_prior_suppression() -> None:
    candidate, refs = _candidate()
    suppressed_candidate = replace(
        candidate,
        review_posture=ReviewPosture.SUPPRESSED,
        suppression_reason=SuppressionReason.MANUAL_SUPPRESSION,
    )
    changed_candidate, changed_refs = _candidate(cash_weight=Decimal("0.21"))
    repository = InMemoryIdeaRepository()
    _persist(repository, suppressed_candidate, refs, sequence=1)

    changed = _persist(
        repository,
        changed_candidate,
        changed_refs,
        sequence=2,
        occurred_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
    )

    assert changed.decision is CandidatePersistenceDecision.MATERIAL_VERSION_CREATED
    assert changed.record is not None
    assert changed.record.candidate.candidate_id == candidate.candidate_id
    assert changed.record.candidate.identity.material_version == 2
    assert changed.record.candidate.identity.evidence_version == 1
    assert changed.record.candidate.identity.supersedes_material_version == 1
    assert changed.record.candidate.identity.change_reason is CandidateChangeReason.MATERIAL_CHANGE
    assert changed.record.candidate.suppression_reason is None
    assert changed.record.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED


@pytest.mark.parametrize(("terminal_status", "terminal_posture"), TERMINAL_STATE_EXPECTATIONS)
def test_evidence_only_correction_preserves_terminal_candidate_state(
    terminal_status: IdeaLifecycleStatus,
    terminal_posture: ReviewPosture,
) -> None:
    candidate, refs = _candidate()
    terminal_candidate = replace(
        candidate,
        lifecycle_status=terminal_status,
        review_posture=terminal_posture,
    )
    corrected_candidate, corrected_refs = _candidate(cashflow_hash="sha256:corrected-cashflow")
    repository = InMemoryIdeaRepository()
    _persist(repository, terminal_candidate, refs, sequence=1)

    corrected = _persist(
        repository,
        corrected_candidate,
        corrected_refs,
        sequence=2,
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )

    assert corrected.decision is CandidatePersistenceDecision.EVIDENCE_REFRESHED
    assert corrected.record is not None
    assert corrected.record.candidate.lifecycle_status is terminal_status
    assert corrected.record.candidate.review_posture is terminal_posture
    assert corrected.record.candidate.identity.material_version == 1
    assert corrected.record.candidate.identity.evidence_version == 2
    assert (
        corrected.record.candidate.identity.change_reason
        is CandidateChangeReason.EVIDENCE_CORRECTION
    )
    assert len(corrected.record.version_history) == 2
    assert corrected.record.version_history[-1].source_lifecycle_status is terminal_status
    assert corrected.record.audit_events[-1].event_type == "idea.candidate.evidence_refreshed"
    assert tuple(repository.snapshot().outbox_events.values())[-1].event_type == (
        "idea.candidate.evidence_refreshed.v1"
    )


@pytest.mark.parametrize(("terminal_status", "terminal_posture"), TERMINAL_STATE_EXPECTATIONS)
def test_next_day_unchanged_economics_preserve_terminal_candidate_state(
    terminal_status: IdeaLifecycleStatus,
    terminal_posture: ReviewPosture,
) -> None:
    candidate, refs = _candidate()
    terminal_candidate = replace(
        candidate,
        lifecycle_status=terminal_status,
        review_posture=terminal_posture,
    )
    next_day = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
    refreshed_candidate, refreshed_refs = _candidate(
        as_of_date=next_day.date(),
        evaluated_at_utc=next_day,
    )
    repository = InMemoryIdeaRepository()
    _persist(repository, terminal_candidate, refs, sequence=1)

    refreshed = _persist(
        repository,
        refreshed_candidate,
        refreshed_refs,
        sequence=2,
        occurred_at_utc=next_day,
    )

    assert refreshed.decision is CandidatePersistenceDecision.EVIDENCE_REFRESHED
    assert refreshed.record is not None
    assert refreshed.record.candidate.lifecycle_status is terminal_status
    assert refreshed.record.candidate.review_posture is terminal_posture
    assert refreshed.record.candidate.identity.material_version == 1
    assert refreshed.record.candidate.identity.evidence_version == 2
    assert (
        refreshed.record.candidate.identity.change_reason
        is CandidateChangeReason.EVIDENCE_CORRECTION
    )
    assert len(refreshed.record.version_history) == 2
    assert refreshed.record.audit_events[-1].event_type == "idea.candidate.evidence_refreshed"
    assert tuple(repository.snapshot().outbox_events.values())[-1].event_type == (
        "idea.candidate.evidence_refreshed.v1"
    )


@pytest.mark.parametrize(("terminal_status", "terminal_posture"), TERMINAL_STATE_EXPECTATIONS)
def test_v2_identity_policy_backfill_preserves_terminal_state_without_false_reopen(
    terminal_status: IdeaLifecycleStatus,
    terminal_posture: ReviewPosture,
) -> None:
    incoming, refs = _candidate()
    existing = replace(
        incoming,
        identity=replace(
            incoming.identity,
            policy_version=PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION,
            material_fingerprint=f"sha256:{'a' * 64}",
        ),
        lifecycle_status=terminal_status,
        review_posture=terminal_posture,
    )
    repository = InMemoryIdeaRepository()
    _persist(repository, existing, refs, sequence=1)

    migrated = _persist(
        repository,
        incoming,
        refs,
        sequence=2,
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )

    assert migrated.decision is CandidatePersistenceDecision.EVIDENCE_REFRESHED
    assert migrated.record is not None
    assert migrated.record.candidate.lifecycle_status is terminal_status
    assert migrated.record.candidate.review_posture is terminal_posture
    assert migrated.record.candidate.identity.policy_version == OPPORTUNITY_IDENTITY_POLICY_VERSION
    assert migrated.record.candidate.identity.material_fingerprint == (
        incoming.identity.material_fingerprint
    )
    assert migrated.record.candidate.identity.material_version == 1
    assert migrated.record.candidate.identity.evidence_version == 2
    assert (
        migrated.record.candidate.identity.change_reason is CandidateChangeReason.MIGRATION_BACKFILL
    )
    assert migrated.record.audit_events[-1].event_type == "idea.candidate.evidence_refreshed"


def test_unknown_identity_policy_change_fails_closed() -> None:
    incoming, refs = _candidate()
    existing = replace(
        incoming,
        identity=replace(incoming.identity, policy_version="idea-opportunity-identity-unknown"),
    )
    repository = InMemoryIdeaRepository()
    accepted = _persist(repository, existing, refs, sequence=1)

    conflict = _persist(repository, incoming, refs, sequence=2)

    assert conflict.decision is CandidatePersistenceDecision.IDENTITY_CONFLICT
    assert conflict.record == accepted.record
    assert conflict.audit_event is None


@pytest.mark.parametrize(("terminal_status", "terminal_posture"), TERMINAL_STATE_EXPECTATIONS)
def test_material_change_reopens_terminal_candidate_as_recurrent_condition(
    terminal_status: IdeaLifecycleStatus,
    terminal_posture: ReviewPosture,
) -> None:
    candidate, refs = _candidate()
    terminal_candidate = replace(
        candidate,
        lifecycle_status=terminal_status,
        review_posture=terminal_posture,
    )
    recurrent_candidate, recurrent_refs = _candidate(cash_weight=Decimal("0.21"))
    repository = InMemoryIdeaRepository()
    _persist(repository, terminal_candidate, refs, sequence=1)

    reopened = _persist(
        repository,
        recurrent_candidate,
        recurrent_refs,
        sequence=2,
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )

    assert reopened.decision is CandidatePersistenceDecision.RECURRENT_CONDITION_REOPENED
    assert reopened.record is not None
    assert reopened.record.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert reopened.record.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert reopened.record.candidate.identity.material_version == 2
    assert reopened.record.candidate.identity.evidence_version == 1
    assert (
        reopened.record.candidate.identity.change_reason
        is CandidateChangeReason.RECURRENT_CONDITION
    )
    assert reopened.record.candidate.identity.supersedes_material_version == 1
    assert reopened.record.version_history[-1].source_lifecycle_status is terminal_status
    assert reopened.record.audit_events[-1].event_type == (
        "idea.candidate.recurrent_condition_reopened"
    )
    assert tuple(repository.snapshot().outbox_events.values())[-1].event_type == (
        "idea.candidate.recurrent_condition_reopened.v1"
    )


def test_candidate_id_collision_with_different_business_identity_is_rejected() -> None:
    candidate, refs = _candidate()
    conflicting = replace(
        candidate,
        identity=replace(
            candidate.identity,
            business_identity_id="opportunity_high_cash_conflicting_scope",
        ),
    )
    repository = InMemoryIdeaRepository()
    accepted = _persist(repository, candidate, refs, sequence=1)

    conflict = repository.persist_candidate(
        conflicting,
        idempotency_key="signal-ingestion:high-cash:002",
        payload={"source_hashes": ["sha256:conflicting-scope"]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
    )

    assert conflict.decision is CandidatePersistenceDecision.IDENTITY_CONFLICT
    assert conflict.audit_event is None
    assert conflict.record == accepted.record
    assert len(repository.snapshot().outbox_events) == 1
