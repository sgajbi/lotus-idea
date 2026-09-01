from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.domain.ranking_evaluation import (
    RANKING_EVALUATION_POLICY_VERSION,
    RankedOpportunityJudgment,
    RankingRelevanceGrade,
    evaluate_ranking_snapshot,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "opportunity_quality"
    / "ranking-quality-golden-set.v1.json"
)
GRADE = {
    "not_useful": RankingRelevanceGrade.NOT_USEFUL,
    "useful": RankingRelevanceGrade.USEFUL,
    "approved_for_conversion": RankingRelevanceGrade.APPROVED_FOR_CONVERSION,
    "downstream_accepted": RankingRelevanceGrade.DOWNSTREAM_ACCEPTED,
}


def _cases() -> list[dict[str, Any]]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "lotus-idea.ranking-quality-golden-set.v1"
    assert payload["methodologyPolicyVersion"] == RANKING_EVALUATION_POLICY_VERSION
    return payload["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["caseId"]))
def test_independently_authored_ranking_quality_golden_set(case: dict[str, Any]) -> None:
    judgments = tuple(
        RankedOpportunityJudgment(
            rank=rank,
            relevance_grade=GRADE[grade] if grade is not None else None,
        )
        for rank, grade in case["judgments"]
    )

    actual = evaluate_ranking_snapshot(
        judgments,
        visible_opportunity_count=case["visibleOpportunityCount"],
        cutoffs=(case["cutoff"],),
    ).cutoff_evaluations[0]

    assert [
        actual.status.value,
        actual.evaluated_depth,
        actual.judged_opportunity_count,
        actual.unjudged_opportunity_count,
        str(actual.judgment_coverage),
        str(actual.precision_at_k) if actual.precision_at_k is not None else None,
        str(actual.ndcg_at_k) if actual.ndcg_at_k is not None else None,
    ] == case["expected"]


@pytest.mark.parametrize(
    "mutation",
    (
        lambda case: case["judgments"].__setitem__(0, [2, case["judgments"][0][1]]),
        lambda case: case["judgments"][0].__setitem__(1, "not_useful"),
        lambda case: case.__setitem__("visibleOpportunityCount", 2),
        lambda case: case.__setitem__("cutoff", 1),
        lambda case: case["expected"].__setitem__(4, "0.500000"),
    ),
)
def test_golden_gate_detects_rank_grade_population_cutoff_and_denominator_mutations(
    mutation: Any,
) -> None:
    case = json.loads(json.dumps(_cases()[0]))
    mutation(case)

    with pytest.raises((AssertionError, ValueError)):
        test_independently_authored_ranking_quality_golden_set(case)
