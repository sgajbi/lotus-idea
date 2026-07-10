from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    ConversionOutcomeIdentity,
    ConversionOutcomePolicyReason,
    ConversionOutcomePolicyViolation,
    ConversionOutcomeStatus,
    ConversionTarget,
    SourceSystem,
    current_conversion_outcome_identity,
    validate_conversion_outcome_progression,
)


EVENT_TIME = datetime(2026, 6, 21, 10, 20, tzinfo=UTC)


def identity(
    status: ConversionOutcomeStatus,
    *,
    outcome_id: str = "outcome-001",
    version: int = 1,
    minute: int = 0,
    supersedes: str | None = None,
    correction_reason: str | None = None,
) -> ConversionOutcomeIdentity:
    return ConversionOutcomeIdentity(
        conversion_outcome_id=outcome_id,
        conversion_intent_id="intent-report-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=version,
        status=status,
        downstream_reference=(
            "report-evidence-001"
            if status in {ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED}
            else None
        ),
        recorded_at_utc=EVENT_TIME + timedelta(minutes=minute),
        actor_subject="lotus-report-worker",
        supersedes_conversion_outcome_id=supersedes,
        correction_reason=correction_reason,
    )


@pytest.mark.parametrize(
    "status",
    (
        ConversionOutcomeStatus.REQUESTED,
        ConversionOutcomeStatus.ACCEPTED,
        ConversionOutcomeStatus.REJECTED,
        ConversionOutcomeStatus.FAILED,
    ),
)
def test_conversion_outcome_policy_accepts_source_owned_initial_postures(
    status: ConversionOutcomeStatus,
) -> None:
    validate_conversion_outcome_progression((), identity(status))


@pytest.mark.parametrize(
    "next_status",
    (
        ConversionOutcomeStatus.ACCEPTED,
        ConversionOutcomeStatus.REJECTED,
        ConversionOutcomeStatus.FAILED,
    ),
)
def test_conversion_outcome_policy_accepts_requested_progression(
    next_status: ConversionOutcomeStatus,
) -> None:
    requested = identity(ConversionOutcomeStatus.REQUESTED)
    proposed = identity(next_status, outcome_id="outcome-002", version=2, minute=1)

    validate_conversion_outcome_progression((requested,), proposed)


def test_conversion_outcome_policy_accepts_accepted_to_completed() -> None:
    accepted = identity(ConversionOutcomeStatus.ACCEPTED)
    completed = identity(
        ConversionOutcomeStatus.COMPLETED,
        outcome_id="outcome-002",
        version=2,
        minute=1,
    )

    validate_conversion_outcome_progression((accepted,), completed)
    assert current_conversion_outcome_identity((completed, accepted)) == completed


def test_conversion_outcome_policy_validates_complete_three_event_history() -> None:
    requested = identity(ConversionOutcomeStatus.REQUESTED)
    accepted = identity(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-002",
        version=2,
        minute=1,
    )
    completed = identity(
        ConversionOutcomeStatus.COMPLETED,
        outcome_id="outcome-003",
        version=3,
        minute=2,
    )

    assert current_conversion_outcome_identity((completed, requested, accepted)) == completed


@pytest.mark.parametrize(
    "terminal_status",
    (
        ConversionOutcomeStatus.REJECTED,
        ConversionOutcomeStatus.FAILED,
        ConversionOutcomeStatus.COMPLETED,
    ),
)
def test_conversion_outcome_policy_rejects_uncorrected_terminal_contradiction(
    terminal_status: ConversionOutcomeStatus,
) -> None:
    terminal = identity(terminal_status)
    contradictory = identity(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-002",
        version=2,
        minute=1,
    )

    with pytest.raises(ConversionOutcomePolicyViolation) as exc_info:
        validate_conversion_outcome_progression((terminal,), contradictory)

    assert exc_info.value.reason is ConversionOutcomePolicyReason.INVALID_TRANSITION


def test_conversion_outcome_policy_allows_append_only_source_correction() -> None:
    rejected = identity(ConversionOutcomeStatus.REJECTED)
    corrected = identity(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-002",
        version=2,
        minute=1,
        supersedes=rejected.conversion_outcome_id,
        correction_reason="Source corrected an erroneous rejection event",
    )

    validate_conversion_outcome_progression((rejected,), corrected)
    assert current_conversion_outcome_identity((rejected, corrected)) == corrected


def test_conversion_outcome_policy_rejects_changed_resource_identity() -> None:
    existing = identity(ConversionOutcomeStatus.ACCEPTED)
    changed_identities = (
        replace(existing, status=ConversionOutcomeStatus.REJECTED),
        replace(existing, source_event_version=2),
        replace(existing, downstream_reference="changed-reference"),
    )

    for changed in changed_identities:
        with pytest.raises(ConversionOutcomePolicyViolation) as exc_info:
            validate_conversion_outcome_progression((existing,), changed)

        assert exc_info.value.reason is ConversionOutcomePolicyReason.IDENTITY_CONFLICT


def test_conversion_outcome_policy_rejects_version_gap_out_of_order_and_unlinked_correction() -> (
    None
):
    accepted = identity(ConversionOutcomeStatus.ACCEPTED)
    invalid_events = (
        (
            identity(
                ConversionOutcomeStatus.COMPLETED,
                outcome_id="gap",
                version=3,
                minute=1,
            ),
            ConversionOutcomePolicyReason.VERSION_CONFLICT,
        ),
        (
            identity(
                ConversionOutcomeStatus.COMPLETED,
                outcome_id="old",
                version=2,
                minute=-1,
            ),
            ConversionOutcomePolicyReason.OUT_OF_ORDER_EVENT,
        ),
        (
            identity(
                ConversionOutcomeStatus.REJECTED,
                outcome_id="correction",
                version=2,
                minute=1,
                supersedes="unknown-outcome",
                correction_reason="Source correction",
            ),
            ConversionOutcomePolicyReason.INVALID_CORRECTION,
        ),
    )

    for proposed, expected_reason in invalid_events:
        with pytest.raises(ConversionOutcomePolicyViolation) as exc_info:
            validate_conversion_outcome_progression((accepted,), proposed)
        assert exc_info.value.reason is expected_reason


def test_invalid_legacy_history_has_no_authoritative_current_posture() -> None:
    rejected = identity(ConversionOutcomeStatus.REJECTED)
    contradictory = identity(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-002",
        version=2,
        minute=1,
    )

    assert current_conversion_outcome_identity((rejected, contradictory)) is None


@pytest.mark.parametrize(
    ("history", "proposed", "expected_reason"),
    [
        (
            (),
            identity(ConversionOutcomeStatus.ACCEPTED, version=2),
            ConversionOutcomePolicyReason.VERSION_CONFLICT,
        ),
        (
            (),
            identity(
                ConversionOutcomeStatus.ACCEPTED,
                supersedes="outcome-previous",
                correction_reason="initial correction is invalid",
            ),
            ConversionOutcomePolicyReason.INVALID_CORRECTION,
        ),
        (
            (identity(ConversionOutcomeStatus.REQUESTED),),
            identity(
                ConversionOutcomeStatus.ACCEPTED,
                outcome_id="outcome-002",
                version=2,
                minute=1,
                correction_reason="unlinked correction",
            ),
            ConversionOutcomePolicyReason.INVALID_CORRECTION,
        ),
        (
            (identity(ConversionOutcomeStatus.ACCEPTED),),
            replace(
                identity(
                    ConversionOutcomeStatus.COMPLETED,
                    outcome_id="outcome-002",
                    version=2,
                    minute=1,
                ),
                conversion_intent_id="different-intent",
            ),
            ConversionOutcomePolicyReason.IDENTITY_CONFLICT,
        ),
        (
            (identity(ConversionOutcomeStatus.REJECTED),),
            identity(
                ConversionOutcomeStatus.ACCEPTED,
                outcome_id="outcome-002",
                version=2,
                minute=1,
                supersedes="outcome-001",
                correction_reason=" ",
            ),
            ConversionOutcomePolicyReason.INVALID_CORRECTION,
        ),
        (
            (identity(ConversionOutcomeStatus.REJECTED),),
            identity(
                ConversionOutcomeStatus.REQUESTED,
                outcome_id="outcome-002",
                version=2,
                minute=1,
                supersedes="outcome-001",
                correction_reason="source correction",
            ),
            ConversionOutcomePolicyReason.INVALID_CORRECTION,
        ),
    ],
)
def test_conversion_outcome_policy_rejects_ambiguous_identity_progressions(
    history: tuple[ConversionOutcomeIdentity, ...],
    proposed: ConversionOutcomeIdentity,
    expected_reason: ConversionOutcomePolicyReason,
) -> None:
    with pytest.raises(ConversionOutcomePolicyViolation) as exc_info:
        validate_conversion_outcome_progression(history, proposed)

    assert exc_info.value.reason is expected_reason
