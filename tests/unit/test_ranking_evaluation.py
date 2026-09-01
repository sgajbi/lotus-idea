from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.ranking_evaluation import (
    RANKING_EVALUATION_POLICY_VERSION,
    RankedOpportunityJudgment,
    RankingCutoffStatus,
    RankingMetricSupportStatus,
    RankingPresentationFact,
    RankingRelevanceGrade,
    aggregate_ranking_evaluations,
    evaluate_ranking_presentations,
    evaluate_ranking_snapshot,
)


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
                presentation_fact(1, RankingRelevanceGrade.NOT_USEFUL),
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
