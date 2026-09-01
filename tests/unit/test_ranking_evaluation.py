from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

import pytest

from app.domain.ranking_evaluation import (
    RANKING_EVALUATION_POLICY_VERSION,
    RankedOpportunityJudgment,
    RankingCutoffStatus,
    RankingJudgmentSource,
    RankingMetricSupportStatus,
    RankingPresentationFact,
    RankingQueueSnapshotEvaluation,
    RankingRelevanceGrade,
    RankingRelevanceFact,
    RankingSnapshotEvaluation,
    aggregate_ranking_evaluations,
    evaluate_ranking_presentations,
    evaluate_ranking_snapshot,
    evaluate_ranking_stability,
    downstream_relevance_grade,
)
from app.domain.ideas import ConversionOutcomeStatus


def judgment(
    rank: int,
    grade: RankingRelevanceGrade | None,
) -> RankedOpportunityJudgment:
    return RankedOpportunityJudgment(rank=rank, relevance_grade=grade)


def presentation_fact(
    rank: int,
    grade: RankingRelevanceGrade | None,
    *,
    digest_character: str = "a",
) -> RankingPresentationFact:
    return RankingPresentationFact(
        queue_snapshot_digest=f"sha256:{digest_character * 64}",
        tenant_id="tenant-a",
        presented_at_utc=datetime(2026, 9, 1, 8, tzinfo=UTC),
        visible_opportunity_count=3,
        queue_policy_version="queue-v1",
        ranking_policy_version="ranking-v1",
        surface="advisor_review_queue",
        producer="lotus-workbench",
        economic_identity_id=f"economic-opportunity-{rank}",
        judgment=judgment(rank, grade),
    )


def test_perfect_ranking_has_full_precision_and_normalized_gain() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.DOWNSTREAM_ACCEPTED),
            judgment(2, RankingRelevanceGrade.APPROVED_FOR_CONVERSION),
            judgment(3, RankingRelevanceGrade.USEFUL),
        ),
        visible_opportunity_count=3,
        cutoffs=(1, 3),
    )

    assert evaluation.policy_version == RANKING_EVALUATION_POLICY_VERSION
    assert evaluation.cutoff_evaluations[0].precision_at_k == Decimal("1.000000")
    assert evaluation.cutoff_evaluations[0].ndcg_at_k == Decimal("1.000000")
    assert evaluation.cutoff_evaluations[1].precision_at_k == Decimal("1.000000")
    assert evaluation.cutoff_evaluations[1].ndcg_at_k == Decimal("1.000000")


def test_reversed_relevance_reduces_ndcg_without_changing_precision() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.USEFUL),
            judgment(2, RankingRelevanceGrade.APPROVED_FOR_CONVERSION),
            judgment(3, RankingRelevanceGrade.DOWNSTREAM_ACCEPTED),
        ),
        visible_opportunity_count=3,
        cutoffs=(3,),
    ).cutoff_evaluations[0]

    assert evaluation.precision_at_k == Decimal("1.000000")
    assert evaluation.ndcg_at_k == Decimal("0.680606")
    assert evaluation.ndcg_at_k < Decimal("1")


def test_presentations_are_grouped_into_deterministic_snapshot_evaluations() -> None:
    evaluations = evaluate_ranking_presentations(
        (
            presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL, digest_character="b"),
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="b"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="b"),
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="a"),
            presentation_fact(2, RankingRelevanceGrade.USEFUL, digest_character="a"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="a"),
        ),
        cutoffs=(3,),
    )

    assert [item.queue_snapshot_digest for item in evaluations] == [
        f"sha256:{'a' * 64}",
        f"sha256:{'b' * 64}",
    ]
    assert evaluations[0].evaluation.cutoff_evaluations[0].precision_at_k == Decimal("0.666667")
    assert evaluations[1].evaluation.cutoff_evaluations[0].precision_at_k == Decimal("0.333333")


@pytest.mark.parametrize(
    "change",
    (
        lambda fact: replace(fact, tenant_id="tenant-b"),
        lambda fact: replace(
            fact,
            presented_at_utc=fact.presented_at_utc + timedelta(seconds=1),
        ),
        lambda fact: replace(fact, visible_opportunity_count=4),
        lambda fact: replace(fact, queue_policy_version="queue-v2"),
        lambda fact: replace(fact, ranking_policy_version="ranking-v2"),
        lambda fact: replace(fact, surface="other-surface"),
        lambda fact: replace(fact, producer="other-producer"),
    ),
)
def test_snapshot_authority_disagreement_is_rejected(
    change: Callable[[RankingPresentationFact], RankingPresentationFact],
) -> None:
    conflicting_fact = change(presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL))
    with pytest.raises(ValueError, match="internally inconsistent"):
        evaluate_ranking_presentations(
            (
                presentation_fact(1, RankingRelevanceGrade.USEFUL),
                conflicting_fact,
            ),
            cutoffs=(1,),
        )


def test_duplicate_snapshot_rank_is_rejected() -> None:
    with pytest.raises(ValueError, match="ranks must be unique"):
        evaluate_ranking_presentations(
            (
                presentation_fact(1, RankingRelevanceGrade.USEFUL),
                replace(
                    presentation_fact(1, RankingRelevanceGrade.NOT_USEFUL),
                    economic_identity_id="different-economic-opportunity",
                ),
            ),
            cutoffs=(1,),
        )


def test_partial_snapshot_receipts_are_incomplete_not_irrelevant() -> None:
    evaluation = evaluate_ranking_presentations(
        (
            presentation_fact(1, RankingRelevanceGrade.USEFUL),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL),
        ),
        cutoffs=(3,),
    )[0].evaluation.cutoff_evaluations[0]

    assert evaluation.status is RankingCutoffStatus.INCOMPLETE_PRESENTATION
    assert evaluation.observed_opportunity_count == 2
    assert evaluation.unjudged_opportunity_count == 1
    assert evaluation.precision_at_k is None
    assert evaluation.ndcg_at_k is None


def test_aggregate_reports_coverage_and_macro_quality_with_support_posture() -> None:
    evaluations = evaluate_ranking_presentations(
        (
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="a"),
            presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL, digest_character="a"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="a"),
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="b"),
            presentation_fact(2, RankingRelevanceGrade.USEFUL, digest_character="b"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="b"),
        ),
        cutoffs=(3,),
    )

    aggregate = aggregate_ranking_evaluations(
        evaluations,
        minimum_ready_snapshot_count=3,
    )[0]

    assert aggregate.snapshot_count == 2
    assert aggregate.ready_snapshot_count == 2
    assert aggregate.judged_opportunity_count == 6
    assert aggregate.evaluated_opportunity_count == 6
    assert aggregate.judgment_coverage == Decimal("1.000000")
    assert aggregate.support_status is RankingMetricSupportStatus.INSUFFICIENT_SUPPORT
    assert aggregate.mean_precision_at_k == Decimal("0.500000")
    assert aggregate.mean_ndcg_at_k == Decimal("1.000000")


def test_aggregate_keeps_incomplete_snapshots_out_of_quality_mean() -> None:
    evaluations = evaluate_ranking_presentations(
        (
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="a"),
            presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL, digest_character="a"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="a"),
            presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="b"),
            presentation_fact(2, None, digest_character="b"),
            presentation_fact(3, RankingRelevanceGrade.NOT_USEFUL, digest_character="b"),
        ),
        cutoffs=(3,),
    )

    aggregate = aggregate_ranking_evaluations(
        evaluations,
        minimum_ready_snapshot_count=1,
    )[0]

    assert aggregate.snapshot_count == 2
    assert aggregate.ready_snapshot_count == 1
    assert aggregate.incomplete_judgment_snapshot_count == 1
    assert aggregate.judgment_coverage == Decimal("0.833333")
    assert aggregate.support_status is RankingMetricSupportStatus.READY
    assert aggregate.mean_precision_at_k == Decimal("0.333333")
    assert aggregate.mean_ndcg_at_k == Decimal("1.000000")


def test_aggregate_with_no_ready_snapshot_exposes_no_quality_value() -> None:
    evaluations = evaluate_ranking_presentations(
        (presentation_fact(1, None),),
        cutoffs=(1,),
    )

    aggregate = aggregate_ranking_evaluations(evaluations)[0]

    assert aggregate.support_status is RankingMetricSupportStatus.UNAVAILABLE
    assert aggregate.judgment_coverage == Decimal("0.000000")
    assert aggregate.mean_precision_at_k is None
    assert aggregate.mean_ndcg_at_k is None


def test_rank_stability_compares_only_equivalent_economic_cohorts() -> None:
    first = evaluate_ranking_presentations(
        tuple(
            presentation_fact(rank, RankingRelevanceGrade.USEFUL, digest_character="a")
            for rank in range(1, 4)
        ),
        cutoffs=(3,),
    )[0]
    reversed_facts = tuple(
        replace(
            presentation_fact(rank, RankingRelevanceGrade.USEFUL, digest_character="b"),
            presented_at_utc=datetime(2026, 9, 1, 9, tzinfo=UTC),
            economic_identity_id=f"economic-opportunity-{4 - rank}",
        )
        for rank in range(1, 4)
    )
    reversed_snapshot = evaluate_ranking_presentations(reversed_facts, cutoffs=(3,))[0]
    unrelated = evaluate_ranking_presentations(
        (
            replace(
                presentation_fact(1, RankingRelevanceGrade.USEFUL, digest_character="c"),
                economic_identity_id="different-economic-opportunity",
            ),
        ),
        cutoffs=(1,),
    )[0]

    stability = evaluate_ranking_stability((first, reversed_snapshot, unrelated))

    assert stability.comparable_snapshot_pair_count == 1
    assert stability.mean_normalized_stability == Decimal("0.000000")


def test_identical_equivalent_ranking_is_fully_stable() -> None:
    first = evaluate_ranking_presentations(
        tuple(
            presentation_fact(rank, RankingRelevanceGrade.USEFUL, digest_character="a")
            for rank in range(1, 4)
        ),
        cutoffs=(3,),
    )[0]
    replay = replace(
        first,
        queue_snapshot_digest=f"sha256:{'b' * 64}",
        presented_at_utc=first.presented_at_utc + timedelta(hours=1),
    )

    stability = evaluate_ranking_stability((first, replay))

    assert stability.comparable_snapshot_pair_count == 1
    assert stability.mean_normalized_stability == Decimal("1.000000")


def test_incomplete_presentations_do_not_contribute_to_stability() -> None:
    incomplete = evaluate_ranking_presentations(
        (presentation_fact(1, RankingRelevanceGrade.USEFUL),),
        cutoffs=(3,),
    )[0]
    replay = replace(
        incomplete,
        queue_snapshot_digest=f"sha256:{'b' * 64}",
        presented_at_utc=incomplete.presented_at_utc + timedelta(hours=1),
    )

    stability = evaluate_ranking_stability((incomplete, replay))

    assert stability.comparable_snapshot_pair_count == 0
    assert stability.mean_normalized_stability is None


@pytest.mark.parametrize("minimum", (0, -1, True))
def test_aggregate_rejects_invalid_minimum_support(minimum: int) -> None:
    with pytest.raises(ValueError, match="minimum_ready_snapshot_count"):
        aggregate_ranking_evaluations((), minimum_ready_snapshot_count=minimum)


def test_unjudged_opportunity_is_not_treated_as_irrelevant() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.USEFUL),
            judgment(2, None),
            judgment(3, RankingRelevanceGrade.NOT_USEFUL),
        ),
        visible_opportunity_count=3,
        cutoffs=(3,),
    ).cutoff_evaluations[0]

    assert evaluation.status is RankingCutoffStatus.INCOMPLETE_JUDGMENTS
    assert evaluation.observed_opportunity_count == 3
    assert evaluation.judged_opportunity_count == 2
    assert evaluation.unjudged_opportunity_count == 1
    assert evaluation.judgment_coverage == Decimal("0.666667")
    assert evaluation.precision_at_k is None
    assert evaluation.ndcg_at_k is None


def test_missing_presentation_rank_fails_closed() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.USEFUL),
            judgment(3, RankingRelevanceGrade.NOT_USEFUL),
        ),
        visible_opportunity_count=3,
        cutoffs=(3,),
    ).cutoff_evaluations[0]

    assert evaluation.status is RankingCutoffStatus.INCOMPLETE_PRESENTATION
    assert evaluation.observed_opportunity_count == 2
    assert evaluation.judgment_coverage == Decimal("0.666667")
    assert evaluation.precision_at_k is None
    assert evaluation.ndcg_at_k is None


def test_all_not_useful_judgments_produce_zero_quality_without_zero_division() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.NOT_USEFUL),
            judgment(2, RankingRelevanceGrade.NOT_USEFUL),
            judgment(3, RankingRelevanceGrade.NOT_USEFUL),
        ),
        visible_opportunity_count=3,
        cutoffs=(3,),
    ).cutoff_evaluations[0]

    assert evaluation.status is RankingCutoffStatus.READY
    assert evaluation.precision_at_k == Decimal("0.000000")
    assert evaluation.ndcg_at_k == Decimal("0.000000")


def test_cutoff_larger_than_visible_queue_reports_actual_evaluated_depth() -> None:
    evaluation = evaluate_ranking_snapshot(
        (
            judgment(1, RankingRelevanceGrade.USEFUL),
            judgment(2, RankingRelevanceGrade.NOT_USEFUL),
        ),
        visible_opportunity_count=2,
        cutoffs=(5,),
    ).cutoff_evaluations[0]

    assert evaluation.cutoff == 5
    assert evaluation.evaluated_depth == 2
    assert evaluation.precision_at_k == Decimal("0.500000")
    assert evaluation.ndcg_at_k == Decimal("1.000000")


@pytest.mark.parametrize(
    ("judgments", "visible_count", "cutoffs", "message"),
    (
        ((judgment(1, RankingRelevanceGrade.USEFUL),) * 2, 2, (1,), "ranks must be unique"),
        ((judgment(2, RankingRelevanceGrade.USEFUL),), 1, (1,), "rank exceeds"),
        ((judgment(1, RankingRelevanceGrade.USEFUL),), 1, (2,), "unsupported ranking cutoffs"),
        ((judgment(1, RankingRelevanceGrade.USEFUL),), 1, (3, 1), "unique and sorted"),
    ),
)
def test_invalid_ranking_evidence_fails_closed(
    judgments: tuple[RankedOpportunityJudgment, ...],
    visible_count: int,
    cutoffs: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_ranking_snapshot(
            judgments,
            visible_opportunity_count=visible_count,
            cutoffs=cutoffs,
        )


@pytest.mark.parametrize(
    ("factory", "message"),
    (
        (
            lambda: RankedOpportunityJudgment(
                rank=cast(int, True),
                relevance_grade=RankingRelevanceGrade.USEFUL,
            ),
            "rank must be a positive integer",
        ),
        (
            lambda: RankedOpportunityJudgment(
                rank=1,
                relevance_grade=cast(RankingRelevanceGrade, 1),
            ),
            "governed ranking vocabulary",
        ),
        (
            lambda: RankingRelevanceFact(
                occurred_at_utc=datetime(2026, 9, 1, 8),
                source=RankingJudgmentSource.ADVISER_REVIEW,
                relevance_grade=RankingRelevanceGrade.USEFUL,
            ),
            "occurred_at_utc must be timezone-aware",
        ),
        (
            lambda: RankingRelevanceFact(
                occurred_at_utc=datetime(2026, 9, 1, 8, tzinfo=UTC),
                source=cast(RankingJudgmentSource, "review"),
                relevance_grade=RankingRelevanceGrade.USEFUL,
            ),
            "governed ranking judgment vocabulary",
        ),
        (
            lambda: RankingRelevanceFact(
                occurred_at_utc=datetime(2026, 9, 1, 8, tzinfo=UTC),
                source=RankingJudgmentSource.ADVISER_REVIEW,
                relevance_grade=cast(RankingRelevanceGrade, 1),
            ),
            "governed ranking vocabulary",
        ),
        (
            lambda: replace(presentation_fact(1, None), tenant_id=" "),
            "tenant_id is required",
        ),
        (
            lambda: replace(
                presentation_fact(1, None),
                presented_at_utc=datetime(2026, 9, 1, 8),
            ),
            "presented_at_utc must be timezone-aware",
        ),
        (
            lambda: replace(
                presentation_fact(1, None),
                judgment=cast(RankedOpportunityJudgment, "invalid"),
            ),
            "judgment must use RankedOpportunityJudgment",
        ),
    ),
)
def test_ranking_value_objects_reject_ungoverned_runtime_values(
    factory: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


@pytest.mark.parametrize(
    ("judgments", "visible_count", "cutoffs", "message"),
    (
        ((), 0, (1,), "visible_opportunity_count"),
        ((judgment(1, None),), 1, (), "cutoffs is required"),
        ((judgment(1, None),), 1, (cast(int, True),), "positive integers"),
        ((cast(RankedOpportunityJudgment, "invalid"),), 1, (1,), "RankedOpportunityJudgment"),
    ),
)
def test_ranking_snapshot_rejects_invalid_runtime_shapes(
    judgments: tuple[RankedOpportunityJudgment, ...],
    visible_count: int,
    cutoffs: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_ranking_snapshot(
            judgments,
            visible_opportunity_count=visible_count,
            cutoffs=cutoffs,
        )


def test_presentation_collection_rejects_invalid_fact_and_duplicate_economic_identity() -> None:
    with pytest.raises(ValueError, match="RankingPresentationFact"):
        evaluate_ranking_presentations((cast(RankingPresentationFact, "invalid"),))

    with pytest.raises(ValueError, match="economic identities must be unique"):
        evaluate_ranking_presentations(
            (
                presentation_fact(1, RankingRelevanceGrade.USEFUL),
                replace(
                    presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL),
                    economic_identity_id="economic-opportunity-1",
                ),
            ),
            cutoffs=(1,),
        )


def test_stability_ignores_empty_evaluation_and_validates_identity_population() -> None:
    empty = RankingQueueSnapshotEvaluation(
        queue_snapshot_digest=f"sha256:{'c' * 64}",
        tenant_id="tenant-a",
        presented_at_utc=datetime(2026, 9, 1, 7, tzinfo=UTC),
        queue_policy_version="queue-v1",
        ranking_policy_version="ranking-v1",
        surface="advisor_review_queue",
        producer="lotus-workbench",
        ranked_economic_identity_ids=(),
        evaluation=RankingSnapshotEvaluation(
            policy_version=RANKING_EVALUATION_POLICY_VERSION,
            visible_opportunity_count=1,
            cutoff_evaluations=(),
        ),
    )
    complete = evaluate_ranking_presentations(
        (
            replace(
                presentation_fact(1, RankingRelevanceGrade.USEFUL),
                visible_opportunity_count=2,
            ),
            replace(
                presentation_fact(2, RankingRelevanceGrade.NOT_USEFUL),
                visible_opportunity_count=2,
            ),
        ),
        cutoffs=(3,),
    )[0]
    duplicate_identity = replace(
        complete,
        ranked_economic_identity_ids=("same", "same"),
    )

    assert evaluate_ranking_stability((empty,)).comparable_snapshot_pair_count == 0
    with pytest.raises(ValueError, match="unique economic identities"):
        evaluate_ranking_stability((duplicate_identity,))


def test_single_opportunity_equivalent_replays_are_fully_stable() -> None:
    first = evaluate_ranking_presentations(
        (presentation_fact(1, RankingRelevanceGrade.USEFUL),),
        cutoffs=(1,),
    )[0]
    replay = replace(
        first,
        queue_snapshot_digest=f"sha256:{'b' * 64}",
        presented_at_utc=first.presented_at_utc + timedelta(hours=1),
    )

    assert evaluate_ranking_stability((first, replay)).mean_normalized_stability == Decimal(
        "1.000000"
    )


def test_non_terminal_downstream_status_is_not_relevance_evidence() -> None:
    assert downstream_relevance_grade(ConversionOutcomeStatus.REQUESTED) is None
