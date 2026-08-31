from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from app.application.runtime_evidence.contract import score_receipt_is_valid


def _component(
    *,
    component: object = "materiality",
    input_score: object = "80",
    weight: object = "1",
    contribution: object = "80.00",
) -> dict[str, object]:
    return {
        "component": component,
        "inputScore": input_score,
        "weight": weight,
        "contribution": contribution,
    }


def _candidate_receipt(**overrides: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "candidateScore": "80.00",
        "scoreReasonCodes": ["materiality_score"],
        "scoreComponents": [_component()],
        "scoreConflictPenaltyApplied": "0",
    }
    receipt.update(overrides)
    return receipt


def test_score_receipt_accepts_exact_reconstructable_candidate_and_abstention() -> None:
    assert score_receipt_is_valid(_candidate_receipt(), candidate_expected=True)
    assert score_receipt_is_valid(
        {
            "candidateScore": None,
            "scoreReasonCodes": [],
            "scoreComponents": [],
            "scoreConflictPenaltyApplied": None,
        },
        candidate_expected=False,
    )


def test_score_receipt_requires_the_complete_contract() -> None:
    receipt = _candidate_receipt()
    del receipt["scoreComponents"]

    assert not score_receipt_is_valid(receipt, candidate_expected=True)


@pytest.mark.parametrize(
    "overrides",
    (
        {"candidateScore": "not-a-decimal"},
        {"scoreConflictPenaltyApplied": object()},
        {"candidateScore": "-0.01"},
        {"candidateScore": "100.01"},
        {"scoreConflictPenaltyApplied": "-0.01"},
        {"scoreConflictPenaltyApplied": "100.01"},
        {"scoreReasonCodes": "materiality_score"},
        {"scoreReasonCodes": []},
        {"scoreReasonCodes": [" "]},
        {"scoreComponents": "materiality"},
        {"scoreComponents": []},
    ),
)
def test_candidate_score_receipt_rejects_invalid_scalar_or_collection_posture(
    overrides: dict[str, object],
) -> None:
    assert not score_receipt_is_valid(
        _candidate_receipt(**overrides),
        candidate_expected=True,
    )


@pytest.mark.parametrize(
    "component",
    (
        "not-a-component-object",
        {"component": "materiality"},
        _component(component="unknown"),
        _component(input_score="not-a-decimal"),
        _component(component="legacy_fixed_policy"),
        _component(input_score="100.01", contribution="100.01"),
        _component(weight="1.01", contribution="80.80"),
        _component(contribution="79.99"),
    ),
)
def test_candidate_score_receipt_rejects_unknown_or_inconsistent_components(
    component: object,
) -> None:
    assert not score_receipt_is_valid(
        _candidate_receipt(scoreComponents=[component]),
        candidate_expected=True,
    )


def test_candidate_score_receipt_rejects_duplicate_components() -> None:
    assert not score_receipt_is_valid(
        _candidate_receipt(scoreComponents=[_component(), deepcopy(_component())]),
        candidate_expected=True,
    )


def test_candidate_score_receipt_rejects_weights_that_do_not_sum_to_one() -> None:
    components: list[dict[str, Any]] = [
        _component(weight="0.50", contribution="40.00"),
        _component(
            component="freshness",
            input_score="100",
            weight="0.25",
            contribution="25.00",
        ),
    ]

    assert not score_receipt_is_valid(
        _candidate_receipt(scoreComponents=components),
        candidate_expected=True,
    )


def test_candidate_score_receipt_rejects_scalar_that_cannot_be_reconstructed() -> None:
    assert not score_receipt_is_valid(
        _candidate_receipt(candidateScore="79.99"),
        candidate_expected=True,
    )
