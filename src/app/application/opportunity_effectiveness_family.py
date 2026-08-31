from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Mapping

from app.domain.ideas import OpportunityFamily
from app.ports.idea_repository import (
    OpportunityEffectivenessRepositorySummary,
    OpportunityFamilyEffectivenessRepositorySummary,
)


RATE_QUANTUM = Decimal("0.000001")


class FamilyEffectivenessDataError(ValueError):
    pass


@dataclass(frozen=True)
class EffectivenessRate:
    numerator: int
    denominator: int
    value: Decimal | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": str(self.value) if self.value is not None else None,
            "zeroDenominatorBehavior": "null",
        }


@dataclass(frozen=True)
class OpportunityFamilyEffectiveness:
    family: OpportunityFamily
    generated_opportunity_count: int
    presented_opportunity_count: int | None
    reviewed_opportunity_count: int
    approved_opportunity_count: int
    rejected_opportunity_count: int
    suppressed_opportunity_count: int
    duplicate_suppressed_opportunity_count: int
    feedback_opportunity_count: int
    conversion_opportunity_count: int
    conversion_intent_count: int
    downstream_accepted_count: int
    downstream_rejected_count: int
    downstream_uncertain_count: int
    presentation_rate: EffectivenessRate | None
    review_rate: EffectivenessRate
    approval_rate: EffectivenessRate
    rejection_rate: EffectivenessRate
    suppression_rate: EffectivenessRate
    duplicate_suppression_rate: EffectivenessRate
    feedback_rate: EffectivenessRate
    conversion_rate: EffectivenessRate
    downstream_accepted_rate: EffectivenessRate
    downstream_rejected_rate: EffectivenessRate
    downstream_uncertain_rate: EffectivenessRate

    def to_payload(self) -> dict[str, Any]:
        return {
            "family": self.family.value,
            "counts": {
                "generatedOpportunityCount": self.generated_opportunity_count,
                "presentedOpportunityCount": self.presented_opportunity_count,
                "reviewedOpportunityCount": self.reviewed_opportunity_count,
                "approvedOpportunityCount": self.approved_opportunity_count,
                "rejectedOpportunityCount": self.rejected_opportunity_count,
                "suppressedOpportunityCount": self.suppressed_opportunity_count,
                "duplicateSuppressedOpportunityCount": (
                    self.duplicate_suppressed_opportunity_count
                ),
                "feedbackOpportunityCount": self.feedback_opportunity_count,
                "conversionOpportunityCount": self.conversion_opportunity_count,
                "conversionIntentCount": self.conversion_intent_count,
                "downstreamAcceptedCount": self.downstream_accepted_count,
                "downstreamRejectedCount": self.downstream_rejected_count,
                "downstreamUncertainCount": self.downstream_uncertain_count,
            },
            "rates": {
                "presentation": (
                    self.presentation_rate.to_payload()
                    if self.presentation_rate is not None
                    else None
                ),
                "review": self.review_rate.to_payload(),
                "approval": self.approval_rate.to_payload(),
                "rejection": self.rejection_rate.to_payload(),
                "suppression": self.suppression_rate.to_payload(),
                "duplicateSuppression": self.duplicate_suppression_rate.to_payload(),
                "feedback": self.feedback_rate.to_payload(),
                "conversion": self.conversion_rate.to_payload(),
                "downstreamAccepted": self.downstream_accepted_rate.to_payload(),
                "downstreamRejected": self.downstream_rejected_rate.to_payload(),
                "downstreamUncertain": self.downstream_uncertain_rate.to_payload(),
            },
        }


def rate(numerator: int, denominator: int) -> EffectivenessRate:
    value = None
    if denominator:
        value = (Decimal(numerator) / Decimal(denominator)).quantize(
            RATE_QUANTUM,
            rounding=ROUND_HALF_EVEN,
        )
    return EffectivenessRate(numerator=numerator, denominator=denominator, value=value)


def summary_counts(summary: OpportunityFamilyEffectivenessRepositorySummary) -> tuple[int, ...]:
    return (
        summary.generated_opportunity_count,
        summary.presented_opportunity_count,
        summary.reviewed_opportunity_count,
        summary.approved_opportunity_count,
        summary.rejected_opportunity_count,
        summary.suppressed_opportunity_count,
        summary.duplicate_suppressed_opportunity_count,
        summary.feedback_opportunity_count,
        summary.conversion_opportunity_count,
        summary.conversion_intent_count,
        summary.downstream_accepted_count,
        summary.downstream_rejected_count,
        summary.downstream_uncertain_count,
    )


def validate_family_effectiveness(summary: OpportunityEffectivenessRepositorySummary) -> None:
    expected_families = {family for family, count in summary.family_counts.items() if count > 0}
    actual_families = {item.family for item in summary.family_effectiveness}
    if actual_families != expected_families or len(actual_families) != len(
        summary.family_effectiveness
    ):
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family funnel must match the generated family cohort"
        )
    for item in summary.family_effectiveness:
        _validate_family_summary(item, summary.family_counts)
    _validate_family_totals(summary)


def _validate_family_totals(summary: OpportunityEffectivenessRepositorySummary) -> None:
    expected = {
        "generated": summary.generated_opportunity_count,
        "presented": summary.presented_opportunity_count,
        "reviewed": summary.reviewed_opportunity_count,
        "approved": summary.latest_review_action_counts.get("approve_for_conversion", 0),
        "rejected": summary.latest_review_action_counts.get("reject", 0),
        "suppressed": summary.suppressed_opportunity_count,
        "duplicate_suppressed": summary.duplicate_suppressed_opportunity_count,
        "feedback": summary.feedback_opportunity_count,
        "conversion": summary.conversion_opportunity_count,
        "conversion_intent": summary.conversion_intent_count,
        "downstream_accepted": (
            summary.current_downstream_outcome_counts.get("accepted", 0)
            + summary.current_downstream_outcome_counts.get("completed", 0)
        ),
        "downstream_rejected": summary.current_downstream_outcome_counts.get("rejected", 0),
        "downstream_uncertain": (
            summary.current_downstream_outcome_counts.get("not_reported", 0)
            + summary.current_downstream_outcome_counts.get("requested", 0)
        ),
    }
    actual = {
        "generated": sum(item.generated_opportunity_count for item in summary.family_effectiveness),
        "presented": sum(item.presented_opportunity_count for item in summary.family_effectiveness),
        "reviewed": sum(item.reviewed_opportunity_count for item in summary.family_effectiveness),
        "approved": sum(item.approved_opportunity_count for item in summary.family_effectiveness),
        "rejected": sum(item.rejected_opportunity_count for item in summary.family_effectiveness),
        "suppressed": sum(
            item.suppressed_opportunity_count for item in summary.family_effectiveness
        ),
        "duplicate_suppressed": sum(
            item.duplicate_suppressed_opportunity_count for item in summary.family_effectiveness
        ),
        "feedback": sum(item.feedback_opportunity_count for item in summary.family_effectiveness),
        "conversion": sum(
            item.conversion_opportunity_count for item in summary.family_effectiveness
        ),
        "conversion_intent": sum(
            item.conversion_intent_count for item in summary.family_effectiveness
        ),
        "downstream_accepted": sum(
            item.downstream_accepted_count for item in summary.family_effectiveness
        ),
        "downstream_rejected": sum(
            item.downstream_rejected_count for item in summary.family_effectiveness
        ),
        "downstream_uncertain": sum(
            item.downstream_uncertain_count for item in summary.family_effectiveness
        ),
    }
    mismatched = sorted(name for name, count in actual.items() if count != expected[name])
    if mismatched:
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family funnel does not reconcile: " + ", ".join(mismatched)
        )


def build_family_effectiveness(
    summaries: tuple[OpportunityFamilyEffectivenessRepositorySummary, ...],
    *,
    presentation_available: bool,
) -> tuple[OpportunityFamilyEffectiveness, ...]:
    return tuple(
        _build_family_effectiveness(item, presentation_available=presentation_available)
        for item in sorted(summaries, key=lambda summary: summary.family)
    )


def _validate_family_summary(
    item: OpportunityFamilyEffectivenessRepositorySummary,
    family_counts: Mapping[str, int],
) -> None:
    generated = item.generated_opportunity_count
    if generated != family_counts.get(item.family, 0):
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family funnel generated count is inconsistent"
        )
    if any(
        value > generated
        for value in (
            item.presented_opportunity_count,
            item.reviewed_opportunity_count,
            item.feedback_opportunity_count,
            item.conversion_opportunity_count,
            item.suppressed_opportunity_count,
            item.duplicate_suppressed_opportunity_count,
        )
    ):
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family funnel exceeds its generated cohort"
        )
    if item.approved_opportunity_count + item.rejected_opportunity_count > (
        item.reviewed_opportunity_count
    ):
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family decisions exceed reviewed opportunities"
        )
    if item.duplicate_suppressed_opportunity_count > item.suppressed_opportunity_count:
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family duplicate suppression exceeds suppression"
        )
    if item.conversion_intent_count < item.conversion_opportunity_count:
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family intents are fewer than converting opportunities"
        )
    if (
        item.downstream_accepted_count
        + item.downstream_rejected_count
        + item.downstream_uncertain_count
        != item.conversion_intent_count
    ):
        raise FamilyEffectivenessDataError(
            "opportunity effectiveness family downstream outcomes do not reconcile"
        )


def _build_family_effectiveness(
    item: OpportunityFamilyEffectivenessRepositorySummary,
    *,
    presentation_available: bool,
) -> OpportunityFamilyEffectiveness:
    return OpportunityFamilyEffectiveness(
        family=OpportunityFamily(item.family),
        generated_opportunity_count=item.generated_opportunity_count,
        presented_opportunity_count=(
            item.presented_opportunity_count if presentation_available else None
        ),
        reviewed_opportunity_count=item.reviewed_opportunity_count,
        approved_opportunity_count=item.approved_opportunity_count,
        rejected_opportunity_count=item.rejected_opportunity_count,
        suppressed_opportunity_count=item.suppressed_opportunity_count,
        duplicate_suppressed_opportunity_count=item.duplicate_suppressed_opportunity_count,
        feedback_opportunity_count=item.feedback_opportunity_count,
        conversion_opportunity_count=item.conversion_opportunity_count,
        conversion_intent_count=item.conversion_intent_count,
        downstream_accepted_count=item.downstream_accepted_count,
        downstream_rejected_count=item.downstream_rejected_count,
        downstream_uncertain_count=item.downstream_uncertain_count,
        presentation_rate=(
            rate(item.presented_opportunity_count, item.generated_opportunity_count)
            if presentation_available
            else None
        ),
        review_rate=rate(item.reviewed_opportunity_count, item.generated_opportunity_count),
        approval_rate=rate(item.approved_opportunity_count, item.reviewed_opportunity_count),
        rejection_rate=rate(item.rejected_opportunity_count, item.reviewed_opportunity_count),
        suppression_rate=rate(item.suppressed_opportunity_count, item.generated_opportunity_count),
        duplicate_suppression_rate=rate(
            item.duplicate_suppressed_opportunity_count,
            item.generated_opportunity_count,
        ),
        feedback_rate=rate(item.feedback_opportunity_count, item.reviewed_opportunity_count),
        conversion_rate=rate(item.conversion_opportunity_count, item.approved_opportunity_count),
        downstream_accepted_rate=rate(item.downstream_accepted_count, item.conversion_intent_count),
        downstream_rejected_rate=rate(item.downstream_rejected_count, item.conversion_intent_count),
        downstream_uncertain_rate=rate(
            item.downstream_uncertain_count, item.conversion_intent_count
        ),
    )


__all__ = [
    "EffectivenessRate",
    "FamilyEffectivenessDataError",
    "OpportunityFamilyEffectiveness",
    "build_family_effectiveness",
    "rate",
    "summary_counts",
    "validate_family_effectiveness",
]
