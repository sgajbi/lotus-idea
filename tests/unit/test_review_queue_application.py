from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashSignalCommand,
    evaluate_and_persist_high_cash_signal,
)
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    build_review_queue_from_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    QueueExclusionReason,
    QueueSnooze,
    ReasonCode,
    SourceRef,
    SourceSystem,
)
from app.domain.access_scope import QueueAccessScopeFilter, ReviewAccessScope


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def source_ref(product_id: str, *, content_hash_suffix: str = "") -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}{content_hash_suffix}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def high_cash_command(
    *,
    cash_weight: Decimal,
    suffix: str = "",
    candidate_scope: ReviewAccessScope | None = None,
) -> EvaluateHighCashSignalCommand:
    return EvaluateHighCashSignalCommand(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref(
            "lotus-core:PortfolioStateSnapshot:v1", content_hash_suffix=suffix
        ),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", content_hash_suffix=suffix),
        cash_movement_ref=source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1", content_hash_suffix=suffix
        ),
        cashflow_projection_ref=source_ref(
            "lotus-core:PortfolioCashflowProjection:v1", content_hash_suffix=suffix
        ),
        evaluated_at_utc=EVALUATED_AT,
        access_scope=candidate_scope,
    )


def access_scope(*, portfolio_id: str = "PB_SG_GLOBAL_BAL_001") -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-private-bank-sg",
        book_id="book-advisor-001",
        portfolio_id=portfolio_id,
        client_id="client-001",
    )


def persist_high_cash_candidate(
    repository: InMemoryIdeaRepository,
    *,
    cash_weight: Decimal = Decimal("0.18"),
    suffix: str = "",
    idempotency_key: str = "signal-ingestion:high-cash:001",
    candidate_scope: ReviewAccessScope | None = None,
) -> str:
    result = evaluate_and_persist_high_cash_signal(
        EvaluateAndPersistHighCashSignalCommand(
            evaluation=high_cash_command(
                cash_weight=cash_weight,
                suffix=suffix,
                candidate_scope=candidate_scope,
            ),
            idempotency_key=idempotency_key,
            actor_subject="signal-ingestion-worker",
        ),
        repository=repository,
    )
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert result.persistence.record is not None
    return result.persistence.record.candidate.candidate_id


def test_build_review_queue_from_repository_projects_persisted_candidates() -> None:
    repository = InMemoryIdeaRepository()
    first_candidate_id = persist_high_cash_candidate(repository)
    second_candidate_id = persist_high_cash_candidate(
        repository,
        cash_weight=Decimal("0.20"),
        suffix="-second",
        idempotency_key="signal-ingestion:high-cash:002",
    )

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT),
        repository=repository,
    )

    assert [item.candidate.candidate_id for item in queue.items] == sorted(
        [first_candidate_id, second_candidate_id]
    )
    assert [item.rank for item in queue.items] == [1, 2]
    assert queue.exclusions == ()


def test_build_review_queue_from_repository_filters_by_advisor_access_scope() -> None:
    repository = InMemoryIdeaRepository()
    included_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-included",
        idempotency_key="signal-ingestion:high-cash:scope-included",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
    )
    excluded_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-excluded",
        idempotency_key="signal-ingestion:high-cash:scope-excluded",
        candidate_scope=access_scope(portfolio_id="PB_SG_ALT_BAL_002"),
    )

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            access_scope_filter=QueueAccessScopeFilter(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                client_id="client-001",
            ),
        ),
        repository=repository,
    )

    assert [item.candidate.candidate_id for item in queue.items] == [included_candidate_id]
    assert queue.exclusions[0].candidate_id == excluded_candidate_id
    assert queue.exclusions[0].reason is QueueExclusionReason.ACCESS_SCOPE_MISMATCH


def test_build_review_queue_from_repository_excludes_expired_candidate_records() -> None:
    repository = InMemoryIdeaRepository()
    candidate_id = persist_high_cash_candidate(repository)
    repository.transition_candidate(
        candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        actor_subject="signal-expiry-worker",
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=datetime(2026, 6, 22, 10, 1, tzinfo=UTC),
        ),
        repository=repository,
    )

    assert queue.items == ()
    assert queue.exclusions[0].candidate_id == candidate_id
    assert queue.exclusions[0].reason is QueueExclusionReason.EXPIRED


def test_build_review_queue_from_repository_applies_snooze_projection() -> None:
    repository = InMemoryIdeaRepository()
    candidate_id = persist_high_cash_candidate(repository)

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            snoozes=(
                QueueSnooze(
                    candidate_id=candidate_id,
                    snoozed_until_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
                    reason_codes=(ReasonCode.REVIEW_REQUIRED,),
                ),
            ),
        ),
        repository=repository,
    )

    assert queue.items == ()
    assert queue.exclusions[0].candidate_id == candidate_id
    assert queue.exclusions[0].reason is QueueExclusionReason.SNOOZED


def test_build_review_queue_from_repository_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )
