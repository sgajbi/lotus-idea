from decimal import Decimal

import pytest

from app.domain.ranking_evaluation import (
    RANKING_EVALUATION_POLICY_VERSION,
    RankedOpportunityJudgment,
    RankingCutoffStatus,
    RankingRelevanceGrade,
    evaluate_ranking_snapshot,
)


def judgment(
    rank: int,
    grade: RankingRelevanceGrade | None,
) -> RankedOpportunityJudgment:
    return RankedOpportunityJudgment(rank=rank, relevance_grade=grade)


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
