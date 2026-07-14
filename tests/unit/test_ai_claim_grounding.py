from dataclasses import dataclass

import pytest

from app.domain.ai_explanation import (
    AI_CLAIM_GROUNDING_POLICY_VERSION,
    render_grounded_claim_narrative,
)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_text: str
    source_product_ids: tuple[str, ...]


def claim(claim_id: str, text: str) -> Claim:
    return Claim(claim_id, text, ("lotus-core:PortfolioStateSnapshot:v1",))


def test_grounded_narrative_is_an_ordered_projection_of_verified_claims() -> None:
    narrative = render_grounded_claim_narrative(
        (
            claim("claim-cash", "Cash is above the governed threshold"),
            claim("claim-review", "Advisor review is warranted."),
        )
    )

    assert narrative == ("Cash is above the governed threshold. Advisor review is warranted.")
    assert AI_CLAIM_GROUNDING_POLICY_VERSION.endswith(".v1")


def test_grounded_narrative_rejects_duplicate_claim_identity() -> None:
    with pytest.raises(ValueError, match="claim_ids must be unique"):
        render_grounded_claim_narrative(
            (claim("claim-duplicate", "First"), claim("claim-duplicate", "Second"))
        )


def test_grounded_narrative_rejects_missing_claims_and_blank_content() -> None:
    with pytest.raises(ValueError, match="grounded claims are required"):
        render_grounded_claim_narrative(())

    with pytest.raises(ValueError, match="claim_text is required"):
        render_grounded_claim_narrative((claim("claim-blank", " "),))
