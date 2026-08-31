from __future__ import annotations

from pydantic import Field

from app.api.base_model import CamelModel
from app.domain import ScoreComponent, ScoreContribution


class ScoreContributionResponse(CamelModel):
    component: ScoreComponent
    input_score: str = Field(..., alias="inputScore")
    weight: str
    contribution: str

    @classmethod
    def from_domain(cls, contribution: ScoreContribution) -> "ScoreContributionResponse":
        return cls(
            component=contribution.component,
            inputScore=str(contribution.input_score),
            weight=str(contribution.weight),
            contribution=str(contribution.contribution),
        )
