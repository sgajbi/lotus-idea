from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Callable

import pytest

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    AdviseRealizationHistoryMutationDecision,
    evaluate_advise_realization_history_mutation,
)


CREATED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


def test_advise_realization_history_accepts_exact_monotonic_owner_chain() -> None:
    history = _history()

    assert history.current_status is AdviseProposalRealizationStatus.ADVISORY_COMPLETED
    assert history.current_source_event_version == 3
    assert history.proposal_record_created is True
    assert history.outcomes[-1].terminal is True


def test_advise_realization_history_rejects_version_gaps_and_identity_drift() -> None:
    history = _history()

    with pytest.raises(ValueError, match="contiguous"):
        replace(
            history,
            outcomes=(
                history.outcomes[0],
                replace(history.outcomes[1], source_event_version=3),
                replace(history.outcomes[2], source_event_version=4),
            ),
            current_source_event_version=4,
        )
    with pytest.raises(ValueError, match="proposal identity changed"):
        replace(
            history,
            outcomes=(
                history.outcomes[0],
                history.outcomes[1],
                replace(history.outcomes[2], proposal_id="proposal-other"),
            ),
            proposal_id="proposal-other",
        )


def test_advise_realization_history_rejects_unsupported_authority_claims() -> None:
    with pytest.raises(ValueError, match="unsupported authority"):
        replace(_history(), order_created=True)


def test_advise_realization_history_rejects_malformed_owner_evidence() -> None:
    history = _history()
    first, linked, completed = history.outcomes
    invalid_histories: tuple[tuple[Callable[[], object], str], ...] = (
        (lambda: replace(history, realization_id=""), "realization_id is required"),
        (lambda: replace(history, source_authority="lotus-core"), "source_authority"),
        (lambda: replace(history, realization_authority="lotus-manage"), "realization_authority"),
        (lambda: replace(history, source_evidence_fingerprint="not-a-digest"), "sha256"),
        (lambda: replace(history, current_source_event_version=0), "must be positive"),
        (
            lambda: replace(history, updated_at_utc=CREATED_AT - timedelta(seconds=1)),
            "must not precede",
        ),
        (lambda: replace(history, outcomes=()), "outcomes are required"),
        (
            lambda: replace(
                history, outcomes=(first, replace(linked, outcome_id=first.outcome_id), completed)
            ),
            "identities must be unique",
        ),
        (
            lambda: replace(
                history,
                outcomes=(
                    replace(first, status=AdviseProposalRealizationStatus.PROPOSAL_LINKED),
                    linked,
                    completed,
                ),
            ),
            "invalid initial status",
        ),
        (
            lambda: replace(
                history,
                outcomes=(
                    first,
                    replace(
                        linked,
                        status=AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
                        terminal=True,
                    ),
                    completed,
                ),
            ),
            "invalid status transition",
        ),
        (
            lambda: replace(
                history,
                outcomes=(
                    first,
                    replace(linked, occurred_at_utc=CREATED_AT - timedelta(seconds=1)),
                    completed,
                ),
            ),
            "must be chronological",
        ),
        (lambda: replace(history, current_source_event_version=2), "final outcome"),
        (
            lambda: replace(
                history, current_status=AdviseProposalRealizationStatus.PROPOSAL_LINKED
            ),
            "current_status",
        ),
        (lambda: replace(history, updated_at_utc=CREATED_AT), "updated_at_utc"),
        (
            lambda: replace(
                history,
                created_at_utc=CREATED_AT - timedelta(seconds=1),
            ),
            "created_at_utc",
        ),
        (lambda: replace(history, review_work_id="iarw_other"), "review_work_id"),
        (
            lambda: replace(history, review_work_id=None, review_work_status=None),
            "review_work_id must match",
        ),
        (
            lambda: replace(
                history,
                outcomes=(first, replace(linked, review_work_id="iarw_other"), completed),
            ),
            "review work identity changed",
        ),
        (lambda: replace(history, proposal_id="proposal-other"), "proposal_id"),
        (lambda: replace(history, proposal_record_created=False), "proposal_record_created"),
    )

    for build_invalid, message in invalid_histories:
        with pytest.raises(ValueError, match=message):
            build_invalid()

    with pytest.raises(ValueError, match="source_event_version must be positive"):
        replace(first, source_event_version=0)
    with pytest.raises(ValueError, match="terminal must match"):
        replace(first, terminal=True)
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(first, occurred_at_utc=CREATED_AT.replace(tzinfo=None))
    with pytest.raises(ValueError, match="must be UTC"):
        replace(first, occurred_at_utc=CREATED_AT.astimezone(timezone(timedelta(hours=1))))


def test_advise_realization_history_rejects_invalid_rejected_before_work_shapes() -> None:
    rejected = AdviseProposalRealizationOutcome(
        outcome_id="ipro_rejected",
        source_event_version=1,
        status=AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
        reason_code="idea_intake_rejected_before_work",
        occurred_at_utc=CREATED_AT,
        review_work_id=None,
        proposal_id=None,
        terminal=True,
    )
    history = replace(
        _history(),
        review_work_id=None,
        review_work_status=None,
        current_status=AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
        current_source_event_version=1,
        proposal_id=None,
        proposal_record_created=False,
        updated_at_utc=CREATED_AT,
        outcomes=(rejected,),
    )

    with pytest.raises(ValueError, match="invalid status transition"):
        replace(
            history,
            current_status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
            current_source_event_version=2,
            updated_at_utc=CREATED_AT + timedelta(minutes=1),
            outcomes=(
                rejected,
                replace(
                    _history().outcomes[1],
                    source_event_version=2,
                    occurred_at_utc=CREATED_AT + timedelta(minutes=1),
                ),
            ),
        )
    with pytest.raises(ValueError, match="forbids review work"):
        replace(
            history,
            review_work_id="iarw_001",
            review_work_status=AdviseProposalReviewWorkStatus.CLOSED,
            outcomes=(replace(rejected, review_work_id="iarw_001"),),
        )


def test_advise_realization_history_mutation_requires_append_only_progression() -> None:
    existing = _history()
    first, linked, completed = existing.outcomes

    assert (
        evaluate_advise_realization_history_mutation(existing, existing)
        is AdviseRealizationHistoryMutationDecision.REPLAYED
    )
    assert (
        evaluate_advise_realization_history_mutation(
            existing, replace(existing, realization_id="ipr_other")
        )
        is AdviseRealizationHistoryMutationDecision.CONFLICT
    )
    assert (
        evaluate_advise_realization_history_mutation(
            existing,
            replace(
                existing,
                outcomes=(first, linked, replace(completed, reason_code="completed_elsewhere")),
            ),
        )
        is AdviseRealizationHistoryMutationDecision.CONFLICT
    )

    pending = replace(
        existing,
        current_status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
        current_source_event_version=2,
        updated_at_utc=linked.occurred_at_utc,
        outcomes=(first, linked),
    )
    assert (
        evaluate_advise_realization_history_mutation(None, pending)
        is AdviseRealizationHistoryMutationDecision.ACCEPTED
    )
    assert (
        evaluate_advise_realization_history_mutation(pending, existing)
        is AdviseRealizationHistoryMutationDecision.ACCEPTED
    )
    assert (
        evaluate_advise_realization_history_mutation(
            pending,
            replace(
                existing,
                outcomes=(
                    replace(first, reason_code="accepted_after_manual_review"),
                    linked,
                    completed,
                ),
            ),
        )
        is AdviseRealizationHistoryMutationDecision.CONFLICT
    )


def _history() -> AdviseProposalRealizationHistory:
    outcomes = (
        AdviseProposalRealizationOutcome(
            outcome_id="ipro_initial",
            source_event_version=1,
            status=AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW,
            reason_code="idea_intake_accepted_for_adviser_review",
            occurred_at_utc=CREATED_AT,
            review_work_id="iarw_001",
            proposal_id=None,
            terminal=False,
        ),
        AdviseProposalRealizationOutcome(
            outcome_id="ipro_linked",
            source_event_version=2,
            status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
            reason_code="advise_proposal_linked",
            occurred_at_utc=CREATED_AT + timedelta(minutes=1),
            review_work_id="iarw_001",
            proposal_id="proposal-001",
            terminal=False,
        ),
        AdviseProposalRealizationOutcome(
            outcome_id="ipro_completed",
            source_event_version=3,
            status=AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
            reason_code="advise_proposal_executed",
            occurred_at_utc=CREATED_AT + timedelta(minutes=2),
            review_work_id="iarw_001",
            proposal_id="proposal-001",
            terminal=True,
        ),
    )
    return AdviseProposalRealizationHistory(
        realization_id="ipr_001",
        intake_id="ipi_001",
        review_work_id="iarw_001",
        review_work_status=AdviseProposalReviewWorkStatus.CLOSED,
        source_authority="lotus-idea",
        realization_authority="lotus-advise",
        tenant_id="tenant-sg",
        legal_entity_code="SGPB",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id="idea-candidate-001",
        conversion_intent_id="conversion-intent-001",
        source_evidence_fingerprint="sha256:evidence-redacted",
        current_status=AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
        current_source_event_version=3,
        proposal_id="proposal-001",
        proposal_record_created=True,
        suitability_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        created_at_utc=CREATED_AT,
        updated_at_utc=CREATED_AT + timedelta(minutes=2),
        outcomes=outcomes,
    )
