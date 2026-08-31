from __future__ import annotations

from decimal import Decimal

from app.domain import IdeaScore, ReasonCode, ScoreComponent, ScoreContribution


def score_fixture(
    *,
    policy_version: str,
    score: Decimal,
    reason_codes: tuple[ReasonCode, ...],
) -> IdeaScore:
    """Build a reconstructable score for tests whose subject is not scoring policy."""
    return IdeaScore(
        policy_version=policy_version,
        score=score,
        reason_codes=reason_codes,
        contributions=(
            ScoreContribution(
                component=ScoreComponent.MATERIALITY,
                input_score=score,
                weight=Decimal("1"),
                contribution=score.quantize(Decimal("0.01")),
            ),
        ),
    )
