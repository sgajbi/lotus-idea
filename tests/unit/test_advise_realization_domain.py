from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
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
