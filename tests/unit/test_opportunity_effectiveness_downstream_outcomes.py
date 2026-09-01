from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from app.application.opportunity_effectiveness import build_opportunity_effectiveness_snapshot
from app.domain import IdeaLifecycleStatus, OpportunityFamily, ReviewPosture
from app.domain.ideas import ConversionOutcomeStatus
from tests.support.opportunity_effectiveness_fixture import (
    FIXTURE_EVALUATED_AT,
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    candidate_fixture,
    conversion_outcome_fixture,
    record_fixture,
    snapshot_fixture,
)


def test_effectiveness_snapshot_measures_terminal_downstream_failure_explicitly() -> None:
    candidate = candidate_fixture(
        "idea-failed-outcome-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("82"),
        created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    record_with_intent = record_fixture(candidate, conversion=True)
    intent = record_with_intent.conversion_intents[0]
    failed = conversion_outcome_fixture(
        intent,
        status=ConversionOutcomeStatus.FAILED,
        version=1,
        recorded_at=FIXTURE_WINDOW_START + timedelta(hours=4),
    )
    snapshot = snapshot_fixture(replace(record_with_intent, conversion_outcomes=(failed,)))

    projection = build_opportunity_effectiveness_snapshot(
        snapshot,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
    )

    outcomes = {
        item.value: item.count
        for item in projection.current_downstream_outcome_counts
        if item.count > 0
    }
    assert outcomes == {ConversionOutcomeStatus.FAILED.value: 1}
    assert projection.downstream_accepted_rate.value == Decimal("0.000000")
    assert projection.downstream_rejected_rate.value == Decimal("0.000000")
    assert projection.downstream_failed_rate.value == Decimal("1.000000")
    assert projection.downstream_uncertain_rate.value == Decimal("0.000000")
    family = projection.family_effectiveness[0]
    assert family.downstream_failed_count == 1
    assert family.downstream_failed_rate.value == Decimal("1.000000")
