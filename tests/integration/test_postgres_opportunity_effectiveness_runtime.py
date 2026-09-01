from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from app.application.opportunity_effectiveness import (
    build_opportunity_effectiveness_snapshot,
    build_opportunity_effectiveness_snapshot_from_summary,
)
from app.domain import (
    CandidatePresentationReceipt,
    FeedbackOutcome,
    FeedbackReason,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReviewAction,
    ReviewPosture,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.support.opportunity_effectiveness_fixture import (
    FIXTURE_EVALUATED_AT,
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    candidate_fixture,
    golden_effectiveness_snapshot,
    record_fixture,
    review_fixture,
    snapshot_fixture,
)


def test_postgres_effectiveness_matches_golden_methodology_and_isolates_tenant(
    postgres_database_url: str,
) -> None:
    golden = golden_effectiveness_snapshot()
    other_tenant = record_fixture(
        candidate_fixture(
            "idea-other-tenant-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("99"),
            created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
            tenant_id="tenant-b",
        )
    )
    persisted = snapshot_fixture(*golden.candidate_records.values(), other_tenant)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(persisted)
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-a",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )
        other_tenant_summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-b",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    expected = build_opportunity_effectiveness_snapshot(
        persisted,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected
    assert actual.snapshot_digest == expected.snapshot_digest
    assert other_tenant_summary.generated_opportunity_count == 1
    assert other_tenant_summary.family_counts == {OpportunityFamily.HIGH_CASH.value: 1}


def test_postgres_effectiveness_empty_cohort_matches_in_memory_methodology(
    postgres_database_url: str,
) -> None:
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-with-no-opportunities",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-with-no-opportunities",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    expected = build_opportunity_effectiveness_snapshot(
        snapshot_fixture(),
        tenant_id="tenant-with-no-opportunities",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected


def test_postgres_effectiveness_attributes_rank_one_acceptance_to_presented_version(
    postgres_database_url: str,
) -> None:
    candidate = candidate_fixture(
        "idea-presented-acceptance-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    record = record_fixture(
        candidate,
        review=review_fixture(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=FIXTURE_WINDOW_START + timedelta(hours=3),
        ),
    )
    receipt = CandidatePresentationReceipt(
        receipt_id="receipt-presented-acceptance-001",
        candidate_id=candidate.candidate_id,
        tenant_id="tenant-a",
        presented_at_utc=FIXTURE_WINDOW_START + timedelta(hours=2),
        rank_at_presentation=1,
        visible_candidate_count=1,
        queue_snapshot_digest=f"sha256:{'9' * 64}",
        queue_policy_version="idea-review-queue-v1",
        ranking_policy_version="idea-score-v2",
        candidate_material_version=candidate.identity.material_version,
        candidate_evidence_version=candidate.identity.evidence_version,
    )
    persisted = replace(
        snapshot_fixture(record),
        presentation_receipts={receipt.receipt_id: receipt},
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(persisted)
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-a",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    expected = build_opportunity_effectiveness_snapshot(
        persisted,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected
    assert actual.presented_opportunity_count == 1
    assert actual.top_ranked_presented_opportunity_count == 1
    assert actual.top_ranked_accepted_opportunity_count == 1
    assert actual.top_ranked_acceptance_rate is not None
    assert actual.top_ranked_acceptance_rate.value == Decimal("1.000000")


def test_postgres_ranked_queue_quality_matches_exact_version_in_memory_projection(
    postgres_database_url: str,
) -> None:
    candidates = tuple(
        candidate_fixture(
            f"idea-postgres-ranked-{index}",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal(95 - index),
            created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
            lifecycle_status=(
                IdeaLifecycleStatus.APPROVED if index == 1 else IdeaLifecycleStatus.GENERATED
            ),
            review_posture=(
                ReviewPosture.APPROVED_FOR_CONVERSION
                if index == 1
                else ReviewPosture.ADVISOR_REVIEW_REQUIRED
            ),
        )
        for index in range(1, 4)
    )
    records = (
        record_fixture(
            candidates[0],
            review=review_fixture(
                candidates[0].candidate_id,
                action=ReviewAction.APPROVE_FOR_CONVERSION,
                decided_at=FIXTURE_WINDOW_START + timedelta(hours=2, minutes=30),
            ),
            conversion=True,
        ),
        record_fixture(
            candidates[1],
            feedback_reason=FeedbackReason.RELEVANT,
            feedback_outcome=FeedbackOutcome.USEFUL,
        ),
        record_fixture(
            candidates[2],
            feedback_reason=FeedbackReason.NOT_RELEVANT,
        ),
    )
    presented_at = FIXTURE_WINDOW_START + timedelta(hours=2)
    receipts = tuple(
        CandidatePresentationReceipt(
            receipt_id=f"receipt-postgres-ranked-{rank}",
            candidate_id=candidate.candidate_id,
            tenant_id="tenant-a",
            presented_at_utc=presented_at,
            rank_at_presentation=rank,
            visible_candidate_count=3,
            queue_snapshot_digest=f"sha256:{'8' * 64}",
            queue_policy_version="idea-review-queue-v1",
            ranking_policy_version="idea-score-v2",
            candidate_material_version=candidate.identity.material_version,
            candidate_evidence_version=candidate.identity.evidence_version,
        )
        for rank, candidate in enumerate(candidates, start=1)
    )
    reordered_receipts = tuple(
        CandidatePresentationReceipt(
            receipt_id=f"receipt-postgres-reordered-{rank}",
            candidate_id=candidate.candidate_id,
            tenant_id="tenant-a",
            presented_at_utc=presented_at + timedelta(minutes=15),
            rank_at_presentation=rank,
            visible_candidate_count=3,
            queue_snapshot_digest=f"sha256:{'7' * 64}",
            queue_policy_version="idea-review-queue-v1",
            ranking_policy_version="idea-score-v2",
            candidate_material_version=candidate.identity.material_version,
            candidate_evidence_version=candidate.identity.evidence_version,
        )
        for rank, candidate in enumerate(reversed(candidates), start=1)
    )
    all_receipts = (*receipts, *reordered_receipts)
    persisted = replace(
        snapshot_fixture(*records),
        presentation_receipts={receipt.receipt_id: receipt for receipt in all_receipts},
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(persisted)
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-a",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    expected = build_opportunity_effectiveness_snapshot(
        persisted,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected
    cutoff_three = next(item for item in actual.ranking_quality if item.cutoff == 3)
    assert cutoff_three.mean_precision_at_k == Decimal("0.666667")
    assert cutoff_three.mean_ndcg_at_k == Decimal("0.770670")
    assert actual.ranking_stability.comparable_snapshot_pair_count == 1
    assert actual.ranking_stability.mean_normalized_stability == Decimal("0.000000")
