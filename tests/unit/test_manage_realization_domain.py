"""The Manage realization model refuses everything the owner machine forbids.

manage#660's review status is deliberately not absorbing - REQUEST_CHANGES
reopens APPROVED and REJECTED reviews - so these tests hold monotonicity where
the owner puts it: the append-only, contiguous event versions. Authority
claims beyond management review are refused at construction, never stored.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    ManageActionRealizationEvent,
    ManageActionRealizationEventType,
    ManageActionRealizationHistory,
    ManageActionRealizationStatus,
    ManageRealizationHistoryMutationDecision,
    evaluate_manage_realization_history_mutation,
)

RECORDED_AT = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)

_EVENT_STEPS: dict[int, tuple[ManageActionRealizationEventType, str | None, str, str, str]] = {
    1: (
        ManageActionRealizationEventType.INTAKE_ACCEPTED,
        None,
        "PENDING_REVIEW",
        "SERVICE",
        "idea_conversion_intent_accepted_for_management_review",
    ),
    2: (
        ManageActionRealizationEventType.APPROVE,
        "PENDING_REVIEW",
        "APPROVED",
        "PORTFOLIO_MANAGER",
        "REVIEW_APPROVED",
    ),
    3: (
        ManageActionRealizationEventType.REQUEST_CHANGES,
        "APPROVED",
        "PENDING_REVIEW",
        "PORTFOLIO_MANAGER",
        "REVIEW_REOPENED_FOR_CHANGES",
    ),
    4: (
        ManageActionRealizationEventType.REJECT,
        "PENDING_REVIEW",
        "REJECTED",
        "DPM_MANAGER",
        "REVIEW_REJECTED_AFTER_CHANGES",
    ),
}


def _event(version: int) -> ManageActionRealizationEvent:
    event_type, previous, status, role, reason = _EVENT_STEPS[version]
    return ManageActionRealizationEvent(
        event_id=f"imae_{version:04d}",
        action_id="ima_001",
        source_event_version=version,
        event_type=event_type,
        previous_status=(ManageActionRealizationStatus(previous) if previous is not None else None),
        status=ManageActionRealizationStatus(status),
        occurred_at_utc=RECORDED_AT + timedelta(minutes=version),
        actor_id="actor-redacted",
        actor_role=role,
        reason_code=reason,
        correlation_id="corr-owner",
        causation_id="conversion-manage_review-001",
    )


def _history(*, version: int) -> ManageActionRealizationHistory:
    events = tuple(_event(item) for item in range(1, version + 1))
    return ManageActionRealizationHistory(
        contract_version="lotus-manage.idea-action-outcome-history.v1",
        intake_id="iai_001",
        management_action_id="ima_001",
        source_authority="lotus-manage",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id="idea-downstream-001",
        conversion_intent_id="conversion-manage_review-001",
        status=events[-1].status,
        source_event_version=version,
        rebalance_execution_proven=False,
        order_execution_proven=False,
        client_publication_proven=False,
        events=events,
    )


def test_the_owner_review_cycle_constructs_including_reopened_reviews() -> None:
    """The full owner path - intake, approval, reopen, rejection - is one
    valid history: exactly what a consumer treating APPROVED as terminal
    would wrongly refuse."""

    history = _history(version=4)

    assert history.status is ManageActionRealizationStatus.REJECTED
    assert history.source_event_version == 4
    assert [event.status.value for event in history.events] == [
        "PENDING_REVIEW",
        "APPROVED",
        "PENDING_REVIEW",
        "REJECTED",
    ]


def test_authority_claims_beyond_management_review_are_refused() -> None:
    with pytest.raises(ValueError, match="unsupported authority"):
        replace(_history(version=2), rebalance_execution_proven=True)
    with pytest.raises(ValueError, match="unsupported authority"):
        replace(_history(version=2), order_execution_proven=True)
    with pytest.raises(ValueError, match="unsupported authority"):
        replace(_history(version=2), client_publication_proven=True)


def test_foreign_contract_versions_and_authorities_are_refused() -> None:
    with pytest.raises(ValueError, match="certified owner contract"):
        replace(_history(version=1), contract_version="lotus-manage.other.v2")
    with pytest.raises(ValueError, match="must be lotus-manage"):
        replace(_history(version=1), source_authority="lotus-advise")


def test_the_first_event_must_be_the_intake_acceptance() -> None:
    history = _history(version=2)
    with pytest.raises(ValueError, match="invalid intake event"):
        replace(
            history,
            events=(
                replace(_event(2), source_event_version=1, event_id="imae_0001"),
                _event(2),
            ),
        )
    with pytest.raises(ValueError, match="intake event must be first"):
        replace(
            history,
            events=(
                _event(1),
                replace(
                    _event(2),
                    event_type=ManageActionRealizationEventType.INTAKE_ACCEPTED,
                ),
            ),
        )


def test_version_gaps_and_duplicate_event_identities_are_refused() -> None:
    history = _history(version=2)
    with pytest.raises(ValueError, match="contiguous from one"):
        replace(history, events=(_event(1), replace(_event(2), source_event_version=3)))
    with pytest.raises(ValueError, match="identities must be unique"):
        replace(history, events=(_event(1), replace(_event(2), event_id="imae_0001")))


def test_broken_chains_and_forbidden_transitions_are_refused() -> None:
    history = _history(version=2)
    with pytest.raises(ValueError, match="chain is not contiguous"):
        replace(
            history,
            events=(
                _event(1),
                replace(
                    _event(2),
                    previous_status=ManageActionRealizationStatus.APPROVED,
                ),
            ),
        )
    # The owner has no REJECTED -> APPROVE transition: a rejected review can
    # only reopen through REQUEST_CHANGES.
    with pytest.raises(ValueError, match="invalid status transition"):
        replace(
            _history(version=4),
            status=ManageActionRealizationStatus.APPROVED,
            source_event_version=5,
            events=(
                *(_event(item) for item in range(1, 5)),
                replace(
                    _event(2),
                    event_id="imae_0005",
                    source_event_version=5,
                    previous_status=ManageActionRealizationStatus.REJECTED,
                    occurred_at_utc=RECORDED_AT + timedelta(minutes=5),
                ),
            ),
        )


def test_chronology_and_action_identity_are_held() -> None:
    history = _history(version=2)
    with pytest.raises(ValueError, match="chronological"):
        replace(
            history,
            events=(
                _event(1),
                replace(_event(2), occurred_at_utc=RECORDED_AT - timedelta(minutes=1)),
            ),
        )
    with pytest.raises(ValueError, match="action identity changed"):
        replace(history, events=(_event(1), replace(_event(2), action_id="ima_002")))


def test_the_summary_must_match_the_final_event() -> None:
    with pytest.raises(ValueError, match="status must match the final event"):
        replace(_history(version=2), status=ManageActionRealizationStatus.PENDING_REVIEW)
    with pytest.raises(ValueError, match="must match the final event"):
        replace(_history(version=2), source_event_version=1)


def test_mutation_evaluation_holds_append_only_monotonicity() -> None:
    """Replay converges, appends progress, and regressions or prefix
    rewrites conflict - including appends that reopen a review, because the
    owner permits them."""

    assert (
        evaluate_manage_realization_history_mutation(None, _history(version=1))
        is ManageRealizationHistoryMutationDecision.ACCEPTED
    )
    assert (
        evaluate_manage_realization_history_mutation(_history(version=2), _history(version=2))
        is ManageRealizationHistoryMutationDecision.REPLAYED
    )
    assert (
        evaluate_manage_realization_history_mutation(_history(version=2), _history(version=3))
        is ManageRealizationHistoryMutationDecision.ACCEPTED
    )
    assert (
        evaluate_manage_realization_history_mutation(_history(version=3), _history(version=2))
        is ManageRealizationHistoryMutationDecision.CONFLICT
    )


def test_mutation_evaluation_refuses_identity_drift_and_prefix_rewrites() -> None:
    assert (
        evaluate_manage_realization_history_mutation(
            _history(version=2),
            replace(_history(version=3), intake_id="iai_002"),
        )
        is ManageRealizationHistoryMutationDecision.CONFLICT
    )
    rewritten = replace(
        _history(version=3),
        events=(
            _event(1),
            replace(_event(2), event_id="imae_rewritten"),
            _event(3),
        ),
    )
    assert (
        evaluate_manage_realization_history_mutation(_history(version=2), rewritten)
        is ManageRealizationHistoryMutationDecision.CONFLICT
    )
