from __future__ import annotations

from typing import Protocol, Sequence

AI_CLAIM_GROUNDING_POLICY_VERSION = "lotus-idea.ai-claim-grounding-policy.v1"


class GroundableClaim(Protocol):
    @property
    def claim_id(self) -> str: ...

    @property
    def claim_text(self) -> str: ...

    @property
    def source_product_ids(self) -> tuple[str, ...]: ...


def render_grounded_claim_narrative(claims: Sequence[GroundableClaim]) -> str:
    """Render advisor-visible text only from claims that passed evidence verification."""
    if not claims:
        raise ValueError("grounded claims are required")
    _require_unique_claim_ids(claims)
    return " ".join(_sentence(claim.claim_text) for claim in claims)


def _require_unique_claim_ids(claims: Sequence[GroundableClaim]) -> None:
    claim_ids = tuple(claim.claim_id for claim in claims)
    if len(set(claim_ids)) != len(claim_ids):
        raise ValueError("claim_ids must be unique")


def _sentence(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("claim_text is required")
    return text if text.endswith((".", "?", "!")) else f"{text}."
