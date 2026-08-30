from __future__ import annotations

from enum import StrEnum


FEEDBACK_TAXONOMY_VERSION = "idea-feedback-taxonomy-v1"


class FeedbackOutcome(StrEnum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"


class FeedbackReason(StrEnum):
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    ALREADY_KNOWN = "already_known"
    WRONG_TIMING = "wrong_timing"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WRONG_PRIORITY = "wrong_priority"
    DUPLICATE = "duplicate"
    CLIENT_SPECIFIC_CONSTRAINT = "client_specific_constraint"


ALLOWED_FEEDBACK_REASONS: dict[FeedbackOutcome, frozenset[FeedbackReason]] = {
    FeedbackOutcome.USEFUL: frozenset({FeedbackReason.RELEVANT}),
    FeedbackOutcome.NOT_USEFUL: frozenset(
        {
            FeedbackReason.NOT_RELEVANT,
            FeedbackReason.ALREADY_KNOWN,
            FeedbackReason.WRONG_TIMING,
            FeedbackReason.INSUFFICIENT_EVIDENCE,
            FeedbackReason.WRONG_PRIORITY,
            FeedbackReason.DUPLICATE,
            FeedbackReason.CLIENT_SPECIFIC_CONSTRAINT,
        }
    ),
}


class InvalidFeedbackTaxonomyCombination(ValueError):
    code = "feedback_taxonomy_combination_invalid"

    def __init__(
        self,
        *,
        taxonomy_version: str,
        outcome: FeedbackOutcome,
        reason: FeedbackReason,
    ) -> None:
        super().__init__(
            "Invalid feedback outcome/reason combination under "
            f"{taxonomy_version}: {outcome.value}/{reason.value}"
        )
        self.taxonomy_version = taxonomy_version
        self.outcome = outcome
        self.reason = reason


def validate_feedback_taxonomy(
    *,
    taxonomy_version: str,
    outcome: FeedbackOutcome,
    reason: FeedbackReason,
) -> None:
    if taxonomy_version != FEEDBACK_TAXONOMY_VERSION:
        raise InvalidFeedbackTaxonomyCombination(
            taxonomy_version=taxonomy_version,
            outcome=outcome,
            reason=reason,
        )
    if reason not in ALLOWED_FEEDBACK_REASONS[outcome]:
        raise InvalidFeedbackTaxonomyCombination(
            taxonomy_version=taxonomy_version,
            outcome=outcome,
            reason=reason,
        )


__all__ = [
    "ALLOWED_FEEDBACK_REASONS",
    "FEEDBACK_TAXONOMY_VERSION",
    "FeedbackOutcome",
    "FeedbackReason",
    "InvalidFeedbackTaxonomyCombination",
    "validate_feedback_taxonomy",
]
