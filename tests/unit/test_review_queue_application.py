from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashSignalCommand,
    evaluate_and_persist_high_cash_signal,
)
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    MAX_REVIEW_QUEUE_PAGE_LIMIT,
    build_review_queue_from_repository,
    build_review_queue_readiness_snapshot,
)
from app.domain import (
    CandidatePersistenceDecision,
    CandidatePersistenceRecord,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    QueueExclusionReason,
    QueueSnooze,
    ReasonCode,
    ReviewQueueSnapshotConflictError,
    ReviewQueuePolicy,
    SourceRef,
    SourceSystem,
    visible_review_queue_candidate_records,
)
from app.domain.access_scope import QueueAccessScopeFilter, ReviewAccessScope
from app.ports.idea_repository import (
    ReviewQueueReadinessRepositorySummary,
    ReviewQueueRepositoryPage,
)


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
    assert queue.page.limit == 25
    assert queue.page.offset == 0
    assert queue.page.returned_item_count == 2
    assert queue.page.total_reviewable_item_count == 2
    assert queue.page.next_offset is None
    assert queue.page.has_next_page is False


def test_build_review_queue_from_repository_pages_reviewable_items_deterministically() -> None:
    repository = InMemoryIdeaRepository()
    candidate_ids = [
        persist_high_cash_candidate(
            repository,
            cash_weight=Decimal("0.18") + Decimal(index) / Decimal("100"),
            suffix=f"-page-{index}",
            idempotency_key=f"signal-ingestion:high-cash:page-{index}",
        )
        for index in range(3)
    ]

    first_page = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=1,
            offset=0,
        ),
        repository=repository,
    )
    second_page = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=1,
            offset=1,
            snapshot_token=first_page.page.snapshot_token,
        ),
        repository=repository,
    )

    assert [item.candidate.candidate_id for item in first_page.items] == [sorted(candidate_ids)[0]]
    assert [item.candidate.candidate_id for item in second_page.items] == [sorted(candidate_ids)[1]]
    assert first_page.page.total_reviewable_item_count == 3
    assert first_page.page.returned_item_count == 1
    assert first_page.page.next_offset == 1
    assert first_page.page.has_next_page is True
    assert second_page.page.offset == 1
    assert second_page.page.next_offset == 2


def test_review_queue_as_of_includes_creation_equality_and_excludes_later_candidate() -> None:
    repository = InMemoryIdeaRepository()
    candidate_id = persist_high_cash_candidate(repository)
    record = repository.snapshot().candidate_records[candidate_id]
    future_record = replace(
        record,
        candidate=replace(
            record.candidate,
            candidate_id="idea_future_candidate",
            source_signal_ids=("signal_future_candidate",),
            created_at_utc=EVALUATED_AT + timedelta(microseconds=1),
            updated_at_utc=EVALUATED_AT + timedelta(microseconds=1),
        ),
    )

    visible = visible_review_queue_candidate_records(
        (record, future_record),
        evaluated_at_utc=EVALUATED_AT,
    )

    assert [item.candidate.candidate_id for item in visible] == [candidate_id]


def test_review_queue_as_of_does_not_reinterpret_source_authority_dates() -> None:
    repository = InMemoryIdeaRepository()
    candidate_id = persist_high_cash_candidate(repository)
    record = repository.snapshot().candidate_records[candidate_id]
    future_source_refs = tuple(
        replace(
            source_ref_item,
            as_of_date=AS_OF_DATE + timedelta(days=1),
            generated_at_utc=EVALUATED_AT + timedelta(days=1),
        )
        for source_ref_item in record.candidate.evidence_packet.source_refs
    )
    evidence_packet = replace(
        record.candidate.evidence_packet,
        source_refs=future_source_refs,
        lineage_ref=replace(
            record.candidate.evidence_packet.lineage_ref,
            source_refs=future_source_refs,
        ),
    )
    source_temporal_record = replace(
        record,
        candidate=replace(record.candidate, evidence_packet=evidence_packet),
    )

    visible = visible_review_queue_candidate_records(
        (source_temporal_record,),
        evaluated_at_utc=EVALUATED_AT,
    )

    assert visible == (source_temporal_record,)


def test_review_queue_continuation_rejects_backdated_candidate_insert() -> None:
    repository = InMemoryIdeaRepository()
    persist_high_cash_candidate(repository)
    persist_high_cash_candidate(
        repository,
        cash_weight=Decimal("0.20"),
        suffix="-snapshot-second",
        idempotency_key="signal-ingestion:high-cash:snapshot-second",
    )
    first_page = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=1,
        ),
        repository=repository,
    )
    persist_high_cash_candidate(
        repository,
        cash_weight=Decimal("0.22"),
        suffix="-snapshot-insert",
        idempotency_key="signal-ingestion:high-cash:snapshot-insert",
    )

    with pytest.raises(ReviewQueueSnapshotConflictError):
        build_review_queue_from_repository(
            BuildReviewQueueFromRepositoryCommand(
                evaluated_at_utc=EVALUATED_AT,
                limit=1,
                offset=1,
                snapshot_token=first_page.page.snapshot_token,
            ),
            repository=repository,
        )


def test_build_review_queue_from_repository_uses_repository_side_page_projection() -> None:
    repository = InMemoryIdeaRepository()
    candidate_ids = [
        persist_high_cash_candidate(
            repository,
            cash_weight=Decimal("0.18") + Decimal(index) / Decimal("100"),
            suffix=f"-repository-page-{index}",
            idempotency_key=f"signal-ingestion:high-cash:repository-page-{index}",
        )
        for index in range(3)
    ]
    snapshot = repository.snapshot()
    second_record = snapshot.candidate_records[sorted(candidate_ids)[1]]

    class RepositorySidePageRepository:
        def __init__(self, record: CandidatePersistenceRecord) -> None:
            self.record = record
            self.snapshot_called = False
            self.requested_limit: int | None = None
            self.requested_offset: int | None = None

        def snapshot(self) -> IdeaRepositorySnapshot:
            self.snapshot_called = True
            raise AssertionError("repository-side queue page must not call snapshot")

        def review_queue_candidate_page(
            self,
            *,
            evaluated_at_utc: datetime,
            expected_snapshot_token: str | None,
            queue_policy_version: str,
            rankable_score_policy_versions: tuple[str, ...],
            access_scope_filter: QueueAccessScopeFilter | None,
            limit: int,
            offset: int,
        ) -> ReviewQueueRepositoryPage:
            assert access_scope_filter is None
            assert evaluated_at_utc == EVALUATED_AT
            assert expected_snapshot_token == "rqs1_" + "a" * 64
            assert queue_policy_version == "idea-deterministic-ranking-v1"
            assert "idle-liquidity-v1" in rankable_score_policy_versions
            self.requested_limit = limit
            self.requested_offset = offset
            return ReviewQueueRepositoryPage(
                candidate_records=(self.record,),
                total_reviewable_item_count=3,
                total_excluded_candidate_count=0,
                snapshot_token="rqs1_" + "a" * 64,
            )

    paged_repository = RepositorySidePageRepository(second_record)

    page = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=1,
            offset=1,
            snapshot_token="rqs1_" + "a" * 64,
        ),
        repository=paged_repository,
    )

    assert paged_repository.snapshot_called is False
    assert paged_repository.requested_limit == 1
    assert paged_repository.requested_offset == 1
    assert [item.candidate.candidate_id for item in page.items] == [
        second_record.candidate.candidate_id
    ]
    assert [item.rank for item in page.items] == [2]
    assert page.exclusions == ()
    assert page.page.total_reviewable_item_count == 3
    assert page.page.returned_item_count == 1
    assert page.page.next_offset == 2


def test_queue_snapshot_binds_rankable_score_policy_set() -> None:
    repository = InMemoryIdeaRepository()
    persist_high_cash_candidate(repository)
    current_policy = ReviewQueuePolicy(
        policy_version="idea-deterministic-ranking-v1",
        rankable_score_policy_versions=("idle-liquidity-v1",),
    )
    expanded_policy = ReviewQueuePolicy(
        policy_version="idea-deterministic-ranking-v1",
        rankable_score_policy_versions=(
            "concentration-attention-v1",
            "idle-liquidity-v1",
        ),
    )
    command = BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT)

    current_page = build_review_queue_from_repository(
        command,
        repository=repository,
        policy=current_policy,
    )
    expanded_page = build_review_queue_from_repository(
        command,
        repository=repository,
        policy=expanded_policy,
    )

    assert current_page.page.snapshot_token != expanded_page.page.snapshot_token


def test_build_review_queue_from_repository_pages_scope_filtered_items_and_exclusions() -> None:
    repository = InMemoryIdeaRepository()
    first_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-scope-page-first",
        idempotency_key="signal-ingestion:high-cash:scope-page-first",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
    )
    second_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-scope-page-second",
        idempotency_key="signal-ingestion:high-cash:scope-page-second",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_002"),
    )
    excluded_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-scope-page-excluded",
        idempotency_key="signal-ingestion:high-cash:scope-page-excluded",
        candidate_scope=access_scope(portfolio_id="PB_SG_OUT_OF_SCOPE_003"),
    )

    page = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=1,
            offset=0,
            access_scope_filter=QueueAccessScopeFilter(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id=("PB_SG_GLOBAL_BAL_001", "PB_SG_GLOBAL_BAL_002"),
                client_id="client-001",
            ),
        ),
        repository=repository,
    )

    assert [item.candidate.candidate_id for item in page.items] == [
        sorted([first_candidate_id, second_candidate_id])[0]
    ]
    assert [exclusion.candidate_id for exclusion in page.exclusions] == [excluded_candidate_id]
    assert page.page.returned_item_count == 1
    assert page.page.total_reviewable_item_count == 2
    assert page.page.returned_exclusion_count == 1
    assert page.page.total_excluded_candidate_count == 1
    assert page.page.next_offset == 1
    assert page.page.has_next_page is True


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


def test_build_review_queue_from_repository_filters_by_multi_portfolio_scope() -> None:
    repository = InMemoryIdeaRepository()
    first_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-first-scope",
        idempotency_key="signal-ingestion:high-cash:multi-scope-first",
        candidate_scope=access_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
    )
    second_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-second-scope",
        idempotency_key="signal-ingestion:high-cash:multi-scope-second",
        candidate_scope=access_scope(portfolio_id="PB_SG_ALT_BAL_002"),
    )
    excluded_candidate_id = persist_high_cash_candidate(
        repository,
        suffix="-third-scope",
        idempotency_key="signal-ingestion:high-cash:multi-scope-third",
        candidate_scope=access_scope(portfolio_id="PB_SG_OFF_SCOPE_003"),
    )

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            access_scope_filter=QueueAccessScopeFilter(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id=("PB_SG_GLOBAL_BAL_001", "PB_SG_ALT_BAL_002"),
                client_id="client-001",
            ),
        ),
        repository=repository,
    )

    assert [item.candidate.candidate_id for item in queue.items] == sorted(
        [first_candidate_id, second_candidate_id]
    )
    assert [exclusion.candidate_id for exclusion in queue.exclusions] == [excluded_candidate_id]
    assert queue.exclusions[0].reason is QueueExclusionReason.ACCESS_SCOPE_MISMATCH


def test_queue_access_scope_filter_rejects_blank_scope_values() -> None:
    with pytest.raises(ValueError, match="scope fields cannot be blank"):
        QueueAccessScopeFilter(portfolio_id=("PB_SG_GLOBAL_BAL_001", " "))


def test_queue_access_scope_filter_handles_empty_scope_and_missing_candidate_scope() -> None:
    assert QueueAccessScopeFilter().matches(None) is True
    assert QueueAccessScopeFilter(portfolio_id="PB_SG_GLOBAL_BAL_001").matches(None) is False


def test_queue_access_scope_filter_allows_unbounded_entitlement_dimensions() -> None:
    requested = QueueAccessScopeFilter(
        tenant_id="tenant-private-bank-sg",
        book_id="book-advisor-001",
        portfolio_id=("PB_SG_GLOBAL_BAL_001", "PB_SG_ALT_BAL_002"),
        client_id="client-001",
    )
    unbounded = QueueAccessScopeFilter()

    assert requested.is_subset_of(unbounded) is True


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


def test_build_review_queue_from_repository_rejects_unsafe_page_controls() -> None:
    with pytest.raises(ValueError, match=f"between 1 and {MAX_REVIEW_QUEUE_PAGE_LIMIT}"):
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            limit=MAX_REVIEW_QUEUE_PAGE_LIMIT + 1,
        )

    with pytest.raises(ValueError, match="offset must be greater than or equal to zero"):
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=EVALUATED_AT,
            offset=-1,
        )


def test_build_review_queue_readiness_snapshot_reports_aggregate_queue_posture() -> None:
    repository = InMemoryIdeaRepository()
    reviewable_candidate_id = persist_high_cash_candidate(repository, suffix="-reviewable")
    expired_candidate_id = persist_high_cash_candidate(
        repository,
        cash_weight=Decimal("0.20"),
        suffix="-expired",
        idempotency_key="signal-ingestion:high-cash:readiness-expired",
    )
    repository.transition_candidate(
        expired_candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        actor_subject="signal-expiry-worker",
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )

    snapshot = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=datetime(2026, 6, 22, 10, 1, tzinfo=UTC),
        ),
        repository=repository,
        durable_storage_backed=False,
    )

    assert snapshot.repository == "lotus-idea"
    assert snapshot.policy_version == "idea-deterministic-ranking-v1"
    assert snapshot.queue_projection_available is True
    assert snapshot.candidate_snapshot_count == 2
    assert snapshot.reviewable_item_count == 1
    assert snapshot.excluded_candidate_count == 1
    assert snapshot.exclusion_counts["expired"] == 1
    assert snapshot.exclusion_counts["unsupported_evidence"] == 0
    assert snapshot.scored_candidate_count == 2
    assert snapshot.unscored_candidate_count == 0
    assert snapshot.durable_storage_backed is False
    assert snapshot.repository_side_pagination_certified is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.certification_blockers == (
        "durable_repository_not_configured",
        "repository_side_queue_pagination_not_certified",
        "workbench_product_proof_missing",
        "data_product_certification_missing",
        "certified_runtime_trust_telemetry_missing",
    )
    assert snapshot.supported_feature_promoted is False
    assert reviewable_candidate_id not in str(snapshot.exclusion_counts)
    assert expired_candidate_id not in str(snapshot.exclusion_counts)


def test_build_review_queue_readiness_snapshot_preserves_non_storage_blockers() -> None:
    repository = InMemoryIdeaRepository()

    snapshot = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT),
        repository=repository,
        durable_storage_backed=True,
    )

    assert snapshot.readiness_status == "blocked"
    assert snapshot.certification_ready is False
    assert "durable_repository_not_configured" not in snapshot.certification_blockers
    assert "repository_side_queue_pagination_not_certified" in snapshot.certification_blockers
    assert "workbench_product_proof_missing" in snapshot.certification_blockers


def test_review_queue_readiness_blocks_unrankable_score_policy() -> None:
    repository = InMemoryIdeaRepository()
    candidate_id = persist_high_cash_candidate(repository, suffix="-stale-policy")
    original = repository.snapshot()
    record = original.candidate_records[candidate_id]
    assert record.candidate.score is not None
    stale_record = replace(
        record,
        candidate=replace(
            record.candidate,
            score=replace(
                record.candidate.score,
                policy_version="idea-deterministic-ranking-v0",
            ),
        ),
    )
    stale_snapshot = replace(
        original,
        candidate_records={candidate_id: stale_record},
    )

    class StaleScoreRepository:
        def snapshot(self) -> IdeaRepositorySnapshot:
            return stale_snapshot

    snapshot = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT),
        repository=StaleScoreRepository(),
        durable_storage_backed=False,
    )

    assert snapshot.reviewable_item_count == 0
    assert snapshot.exclusion_counts["unrankable_score_policy"] == 1
    assert "review_queue_score_policy_coverage_incomplete" in snapshot.certification_blockers


def test_build_review_queue_readiness_snapshot_clears_repository_side_pagination_blocker() -> None:
    class RepositorySideReadinessRepository:
        def __init__(self) -> None:
            self.readiness_summary_count = 0

        def snapshot(self) -> IdeaRepositorySnapshot:
            raise AssertionError("readiness projection should not hydrate the full snapshot")

        def review_queue_readiness_summary(
            self,
            *,
            evaluated_at_utc: datetime,
            rankable_score_policy_versions: tuple[str, ...],
            access_scope_filter: QueueAccessScopeFilter | None,
        ) -> ReviewQueueReadinessRepositorySummary:
            assert access_scope_filter is None
            assert evaluated_at_utc == EVALUATED_AT
            assert "idle-liquidity-v1" in rankable_score_policy_versions
            self.readiness_summary_count += 1
            return ReviewQueueReadinessRepositorySummary(
                candidate_snapshot_count=2,
                reviewable_item_count=1,
                excluded_candidate_count=1,
                exclusion_counts={reason.value: 0 for reason in QueueExclusionReason}
                | {QueueExclusionReason.EXPIRED.value: 1},
                scored_candidate_count=2,
                unscored_candidate_count=0,
            )

    repository = RepositorySideReadinessRepository()
    snapshot = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT),
        repository=repository,
        durable_storage_backed=True,
    )

    assert repository.readiness_summary_count == 1
    assert snapshot.repository_side_pagination_certified is True
    assert snapshot.candidate_snapshot_count == 2
    assert snapshot.reviewable_item_count == 1
    assert snapshot.excluded_candidate_count == 1
    assert snapshot.exclusion_counts["expired"] == 1
    assert "repository_side_queue_pagination_not_certified" not in snapshot.certification_blockers
    assert "workbench_product_proof_missing" in snapshot.certification_blockers
    assert "data_product_certification_missing" in snapshot.certification_blockers


def test_build_review_queue_readiness_snapshot_falls_back_to_snapshot_once() -> None:
    repository = InMemoryIdeaRepository()
    persist_high_cash_candidate(repository)

    class CountingRepository:
        def __init__(self, wrapped: InMemoryIdeaRepository) -> None:
            self.wrapped = wrapped
            self.snapshot_count = 0

        def snapshot(self) -> IdeaRepositorySnapshot:
            self.snapshot_count += 1
            return self.wrapped.snapshot()

    counting_repository = CountingRepository(repository)

    build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=EVALUATED_AT),
        repository=counting_repository,
        durable_storage_backed=False,
    )

    assert counting_repository.snapshot_count == 1
