from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest

from app.domain.feedback_taxonomy import FeedbackOutcome
from app.domain.ideas import ConversionOutcomeStatus
from app.domain.ranking_evaluation import (
    RANKING_EVALUATION_POLICY_VERSION,
    RankingJudgmentSource,
    RankingRelevanceFact,
    RankingRelevanceGrade,
    derive_ranking_relevance,
    downstream_relevance_grade,
    feedback_relevance_grade,
    review_relevance_grade,
)
from app.domain.review_governance import ReviewAction


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "opportunity_quality"
    / "ranking-relevance-golden-set.v1.json"
)
GRADE_BY_NAME = {grade.name.lower(): grade for grade in RankingRelevanceGrade}
SOURCE_BY_KIND = {
    "review": RankingJudgmentSource.ADVISER_REVIEW,
    "feedback": RankingJudgmentSource.ADVISER_FEEDBACK,
    "downstream": RankingJudgmentSource.DOWNSTREAM_OUTCOME,
}


def _payload() -> dict[str, Any]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "lotus-idea.ranking-relevance-golden-set.v1"
    assert payload["methodologyPolicyVersion"] == RANKING_EVALUATION_POLICY_VERSION
    return payload


def _time(hour: int) -> datetime:
    return datetime(2026, 9, 1, hour, tzinfo=UTC)


def _grade(fact: dict[str, Any]) -> RankingRelevanceGrade | None:
    if fact["kind"] == "review":
        return review_relevance_grade(ReviewAction(fact["value"]))
    if fact["kind"] == "feedback":
        return feedback_relevance_grade(FeedbackOutcome(fact["value"]))
    return downstream_relevance_grade(ConversionOutcomeStatus(fact["value"]))


@pytest.mark.parametrize(
    "case",
    _payload()["cases"],
    ids=lambda case: str(case["caseId"]),
)
def test_independently_authored_ranking_relevance_golden_set(case: dict[str, Any]) -> None:
    payload = _payload()
    facts = tuple(
        RankingRelevanceFact(
            occurred_at_utc=_time(fact["hour"]),
            source=SOURCE_BY_KIND[fact["kind"]],
            relevance_grade=grade,
        )
        for fact in case["facts"]
        if (grade := _grade(fact)) is not None
    )
    valid_until_hour = case["validUntilHour"]

    if expected_error := case.get("expectedError"):
        with pytest.raises(ValueError, match=expected_error):
            derive_ranking_relevance(
                facts,
                presented_at_utc=_time(payload["presentedAtHour"]),
                evaluated_at_utc=_time(payload["evaluatedAtHour"]),
                valid_until_utc=(_time(valid_until_hour) if valid_until_hour is not None else None),
            )
        return

    actual = derive_ranking_relevance(
        facts,
        presented_at_utc=_time(payload["presentedAtHour"]),
        evaluated_at_utc=_time(payload["evaluatedAtHour"]),
        valid_until_utc=_time(valid_until_hour) if valid_until_hour is not None else None,
    )

    expected = case["expectedGrade"]
    assert actual == (GRADE_BY_NAME[expected] if expected is not None else None)
