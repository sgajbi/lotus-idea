from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    EvidenceReplayStatus,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)


AS_OF_DATE = datetime(2026, 6, 21, 10, 0, tzinfo=UTC).date()
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    content_hash: str | None = None,
) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolio_id}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/cash-balances",
        "lotus-core:PortfolioCashMovementSummary:v1": "/portfolios/{portfolio_id}/cash-movement-summary",
        "lotus-core:PortfolioCashflowProjection:v1": "/portfolios/{portfolio_id}/cashflow-projection",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=content_hash or f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def high_cash_candidate_source_refs(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    cashflow_hash: str | None = None,
) -> tuple[SourceRef, ...]:
    return (
        source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness=freshness),
        source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness=freshness),
        source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            freshness=freshness,
            content_hash=cashflow_hash,
        ),
    )


def high_cash_candidate() -> tuple[IdeaCandidate, tuple[SourceRef, ...]]:
    refs = high_cash_candidate_source_refs()
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=AS_OF_DATE,
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=EVALUATED_AT,
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    assert result.candidate is not None
    return result.candidate, refs


def test_persist_candidate_accepts_once_and_replays_same_idempotency_payload() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()

    first = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    second = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert first.decision is CandidatePersistenceDecision.ACCEPTED
    assert second.decision is CandidatePersistenceDecision.REPLAYED
    assert first.record == second.record
    assert first.record is not None
    assert len(first.record.audit_events) == 1
    assert first.record.audit_events[0].event_type == "idea.candidate.persisted"


def test_persist_candidate_rejects_idempotency_conflict_without_extra_audit_event() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    conflict = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": ["sha256:different"]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert conflict.decision is CandidatePersistenceDecision.CONFLICT
    assert conflict.audit_event is None
    assert conflict.record is not None
    assert len(conflict.record.audit_events) == 1


def test_duplicate_candidate_identity_is_not_persisted_twice() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    duplicate = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:002",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert duplicate.decision is CandidatePersistenceDecision.DUPLICATE_CANDIDATE
    assert duplicate.record is not None
    assert len(duplicate.record.audit_events) == 1


def test_replay_matches_hash_or_returns_stale_and_mismatch_posture() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    matched = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=EVALUATED_AT,
    )
    stale = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=high_cash_candidate_source_refs(freshness=EvidenceFreshness.STALE),
        evaluated_at_utc=EVALUATED_AT,
    )
    mismatch = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=high_cash_candidate_source_refs(
            cashflow_hash="sha256:changed-cashflow"
        ),
        evaluated_at_utc=EVALUATED_AT,
    )

    assert matched.status is EvidenceReplayStatus.MATCHED
    assert matched.current_evidence_hash == persisted.record.evidence_hash
    assert stale.status is EvidenceReplayStatus.STALE_SOURCE
    assert mismatch.status is EvidenceReplayStatus.HASH_MISMATCH


def test_expired_candidate_replay_returns_expired_posture_with_audit_history() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    expired = repository.transition_candidate(
        persisted.record.candidate.candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        actor_subject="signal-expiry-worker",
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )
    replay = repository.replay_evidence(
        expired.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=datetime(2026, 6, 22, 10, 1, tzinfo=UTC),
    )

    assert replay.status is EvidenceReplayStatus.EXPIRED
    assert expired.lifecycle_history[-1].target_status is IdeaLifecycleStatus.EXPIRED
    assert expired.audit_events[-1].event_type == "idea.lifecycle.transitioned"


def test_repository_snapshot_recovers_candidate_idempotency_and_replay_state() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    recovered = InMemoryIdeaRepository(repository.snapshot())
    replayed = recovered.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    replay = recovered.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert replayed.decision is CandidatePersistenceDecision.REPLAYED
    assert replay.status is EvidenceReplayStatus.MATCHED
