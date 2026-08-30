from __future__ import annotations

import pytest

from app.domain import (
    ALLOWED_FEEDBACK_REASONS,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackOutcome,
    FeedbackReason,
    InvalidFeedbackTaxonomyCombination,
    validate_feedback_taxonomy,
)


ALL_COMBINATIONS = tuple(
    (outcome, reason) for outcome in FeedbackOutcome for reason in FeedbackReason
)


@pytest.mark.parametrize(
    ("outcome", "reason"),
    tuple(
        (outcome, reason)
        for outcome, reasons in ALLOWED_FEEDBACK_REASONS.items()
        for reason in sorted(reasons, key=lambda item: item.value)
    ),
)
def test_every_governed_feedback_combination_is_accepted(
    outcome: FeedbackOutcome,
    reason: FeedbackReason,
) -> None:
    validate_feedback_taxonomy(
        taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
        outcome=outcome,
        reason=reason,
    )


@pytest.mark.parametrize(
    ("outcome", "reason"),
    tuple(
        combination
        for combination in ALL_COMBINATIONS
        if combination[1] not in ALLOWED_FEEDBACK_REASONS[combination[0]]
    ),
)
def test_every_undefined_feedback_combination_fails_closed(
    outcome: FeedbackOutcome,
    reason: FeedbackReason,
) -> None:
    with pytest.raises(InvalidFeedbackTaxonomyCombination) as exc_info:
        validate_feedback_taxonomy(
            taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
            outcome=outcome,
            reason=reason,
        )

    assert exc_info.value.code == "feedback_taxonomy_combination_invalid"
    assert exc_info.value.outcome is outcome
    assert exc_info.value.reason is reason


def test_unknown_feedback_taxonomy_version_fails_closed() -> None:
    with pytest.raises(InvalidFeedbackTaxonomyCombination) as exc_info:
        validate_feedback_taxonomy(
            taxonomy_version="idea-feedback-taxonomy-v2",
            outcome=FeedbackOutcome.USEFUL,
            reason=FeedbackReason.RELEVANT,
        )

    assert exc_info.value.taxonomy_version == "idea-feedback-taxonomy-v2"
