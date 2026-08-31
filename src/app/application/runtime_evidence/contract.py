from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain import ScoreComponent


SCORE_RECEIPT_KEYS = frozenset(
    {
        "candidateScore",
        "scoreReasonCodes",
        "scoreComponents",
        "scoreConflictPenaltyApplied",
    }
)


def non_authority_claims_are_valid(
    claims: Mapping[str, Any],
    *,
    owners: Mapping[str, str],
) -> bool:
    return all(claims.get(key) == value for key, value in owners.items()) and all(
        value is False for key, value in claims.items() if key not in owners
    )


def score_receipt_is_valid(receipt: Mapping[str, Any], *, candidate_expected: bool) -> bool:
    if not SCORE_RECEIPT_KEYS.issubset(receipt):
        return False
    if not candidate_expected:
        return (
            receipt.get("candidateScore") is None
            and receipt.get("scoreReasonCodes") == []
            and receipt.get("scoreComponents") == []
            and receipt.get("scoreConflictPenaltyApplied") is None
        )
    try:
        score = Decimal(str(receipt.get("candidateScore")))
        penalty = Decimal(str(receipt.get("scoreConflictPenaltyApplied")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    reason_codes = receipt.get("scoreReasonCodes")
    components = receipt.get("scoreComponents")
    if (
        score < Decimal("0")
        or score > Decimal("100")
        or penalty < Decimal("0")
        or penalty > Decimal("100")
        or not isinstance(reason_codes, list)
        or not reason_codes
        or not all(isinstance(value, str) and value.strip() for value in reason_codes)
        or not isinstance(components, list)
        or not components
    ):
        return False
    parsed = [_score_component(item) for item in components]
    if any(item is None for item in parsed):
        return False
    contributions = [item for item in parsed if item is not None]
    if len({item[0] for item in contributions}) != len(contributions):
        return False
    if sum((item[2] for item in contributions), Decimal("0")) != Decimal("1"):
        return False
    total = sum((item[3] for item in contributions), Decimal("0"))
    expected = min(
        Decimal("100"),
        max(
            Decimal("0"),
            (total - penalty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        ),
    )
    return score == expected


def _score_component(value: object) -> tuple[ScoreComponent, Decimal, Decimal, Decimal] | None:
    if not isinstance(value, Mapping) or set(value) != {
        "component",
        "inputScore",
        "weight",
        "contribution",
    }:
        return None
    try:
        component = ScoreComponent(str(value.get("component")))
        input_score = Decimal(str(value.get("inputScore")))
        weight = Decimal(str(value.get("weight")))
        contribution = Decimal(str(value.get("contribution")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    expected_contribution = (input_score * weight).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    if (
        component is ScoreComponent.LEGACY_FIXED_POLICY
        or input_score < Decimal("0")
        or input_score > Decimal("100")
        or weight < Decimal("0")
        or weight > Decimal("1")
        or contribution != expected_contribution
    ):
        return None
    return component, input_score, weight, contribution
