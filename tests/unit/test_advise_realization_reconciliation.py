from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest

from app.application.advise_realization_reconciliation import (
    AdviseRealizationAccessScopeDenied,
    AdviseRealizationReconciliationStatus,
    ReconcileAdviseRealizationCommand,
    reconcile_advise_realization_history,
)
from app.application.downstream_realization import (
    RealizeConversionIntentCommand,
    submit_conversion_intent_to_downstream,
)
from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    ConversionTarget,
    InMemoryIdeaRepository,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationReadError,
    DownstreamRealizationOutcome,
)
from tests.unit.test_downstream_realization_application import (
    CapturingAdviseClient,
    repository_with_conversion,
)


RECORDED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
AUTHORIZED_SCOPE = QueueAccessScopeFilter(
    tenant_id="tenant-sg",
    book_id="book-private-bank-sg",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-redacted",
)


@dataclass
class StubAdviseReader:
    history: AdviseProposalRealizationHistory
    calls: int = 0

    def load_proposal_realization(
        self,
        *,
        intake_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AdviseProposalRealizationHistory:
        self.calls += 1
        assert intake_id == "ipi_001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        return self.history


def test_reconcile_advise_history_persists_append_only_owner_evidence() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubAdviseReader(_history(version=2))

    accepted = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=reader,
    )
    replayed = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=reader,
    )
    reader.history = _history(version=3)
    progressed = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=reader,
    )

    assert accepted.status is AdviseRealizationReconciliationStatus.ACCEPTED
    assert accepted.appended_outcome_count == 2
    assert replayed.status is AdviseRealizationReconciliationStatus.REPLAYED
    assert replayed.appended_outcome_count == 0
    assert progressed.status is AdviseRealizationReconciliationStatus.ACCEPTED
    assert progressed.appended_outcome_count == 1
    assert progressed.history is not None
    assert progressed.history.current_status is AdviseProposalRealizationStatus.ADVISORY_COMPLETED
    assert progressed.grants_execution_authority is False
    assert progressed.grants_suitability_authority is False
    assert progressed.grants_client_publication_authority is False


def test_reconcile_advise_history_fails_closed_on_owner_identity_drift() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubAdviseReader(replace(_history(version=2), portfolio_id="PB_OTHER"))

    result = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=reader,
    )

    assert result.status is AdviseRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "advise_realization_scope_conflict"
    assert repository.advise_realization_history_by_support_reference(support_reference) is None


def test_reconcile_advise_history_denies_scope_before_owner_call() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubAdviseReader(_history(version=2))

    with pytest.raises(AdviseRealizationAccessScopeDenied):
        reconcile_advise_realization_history(
            replace(
                _command(support_reference),
                access_scope_filter=replace(AUTHORIZED_SCOPE, portfolio_id=("PB_OTHER",)),
            ),
            repository=repository,
            advise_reader=reader,
        )

    assert reader.calls == 0


def test_reconcile_terminal_rejection_persists_owner_history() -> None:
    repository, support_reference = _repository_with_rejected_submission()
    reader = StubAdviseReader(_rejected_history())

    result = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=reader,
    )

    assert result.status is AdviseRealizationReconciliationStatus.ACCEPTED
    assert result.appended_outcome_count == 1
    assert result.history is not None
    assert result.history.current_status is AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK
    assert result.history.review_work_id is None
    assert result.history.proposal_record_created is False


def test_reconcile_maps_owner_read_failure_without_infrastructure_dependency() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    class UnavailableReader:
        def load_proposal_realization(self, **_kwargs: object) -> AdviseProposalRealizationHistory:
            raise DownstreamRealizationReadError("owner unavailable")

    result = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=UnavailableReader(),
    )

    assert result.status is AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE
    assert result.blocker == "advise_realization_owner_unavailable"


def _repository_with_accepted_submission() -> tuple[InMemoryIdeaRepository, str]:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="submission-advise-owner-history-001",
            actor_subject="advisor-redacted",
            access_scope_filter=AUTHORIZED_SCOPE,
            submitted_at_utc=RECORDED_AT,
        ),
        repository=repository,
        advise_client=CapturingAdviseClient(
            DownstreamRealizationOutcome.accepted_by_downstream(
                DownstreamOwnerReceipt(
                    owner_authority=SourceSystem.LOTUS_ADVISE,
                    owner_request_id="ipi_001",
                    owner_realization_id="ipr_001",
                    owner_work_id="iarw_001",
                    source_event_version=1,
                    source_evidence_fingerprint="sha256:downstream-evidence",
                )
            )
        ),
        manage_client=None,
    )
    assert result.support_reference is not None
    return repository, result.support_reference


def _repository_with_rejected_submission() -> tuple[InMemoryIdeaRepository, str]:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="submission-advise-owner-rejected-001",
            actor_subject="advisor-redacted",
            access_scope_filter=AUTHORIZED_SCOPE,
            submitted_at_utc=RECORDED_AT,
        ),
        repository=repository,
        advise_client=CapturingAdviseClient(
            DownstreamRealizationOutcome.rejected_by_downstream(
                "downstream_rejected",
                owner_receipt=DownstreamOwnerReceipt(
                    owner_authority=SourceSystem.LOTUS_ADVISE,
                    owner_request_id="ipi_001",
                    owner_realization_id="ipr_001",
                    owner_work_id=None,
                    source_event_version=1,
                    source_evidence_fingerprint="sha256:downstream-evidence",
                ),
            )
        ),
        manage_client=None,
    )
    assert result.support_reference is not None
    return repository, result.support_reference


def _command(support_reference: str) -> ReconcileAdviseRealizationCommand:
    return ReconcileAdviseRealizationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE,
        correlation_id="corr-advise-history",
        trace_id="trace-advise-history",
    )


def _history(*, version: int) -> AdviseProposalRealizationHistory:
    outcomes = [
        AdviseProposalRealizationOutcome(
            outcome_id="ipro_001",
            source_event_version=1,
            status=AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW,
            reason_code="idea_intake_accepted_for_adviser_review",
            occurred_at_utc=RECORDED_AT,
            review_work_id="iarw_001",
            proposal_id=None,
            terminal=False,
        ),
        AdviseProposalRealizationOutcome(
            outcome_id="ipro_002",
            source_event_version=2,
            status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
            reason_code="advise_proposal_linked",
            occurred_at_utc=RECORDED_AT + timedelta(minutes=1),
            review_work_id="iarw_001",
            proposal_id="proposal-001",
            terminal=False,
        ),
    ]
    if version == 3:
        outcomes.append(
            AdviseProposalRealizationOutcome(
                outcome_id="ipro_003",
                source_event_version=3,
                status=AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
                reason_code="advise_proposal_executed",
                occurred_at_utc=RECORDED_AT + timedelta(minutes=2),
                review_work_id="iarw_001",
                proposal_id="proposal-001",
                terminal=True,
            )
        )
    final = outcomes[-1]
    return AdviseProposalRealizationHistory(
        realization_id="ipr_001",
        intake_id="ipi_001",
        review_work_id="iarw_001",
        review_work_status=(
            AdviseProposalReviewWorkStatus.CLOSED
            if version == 3
            else AdviseProposalReviewWorkStatus.PROPOSAL_LINKED
        ),
        source_authority="lotus-idea",
        realization_authority="lotus-advise",
        tenant_id="tenant-sg",
        legal_entity_code="SGPB",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id="idea-downstream-001",
        conversion_intent_id="conversion-advise_proposal-001",
        source_evidence_fingerprint="sha256:downstream-evidence",
        current_status=final.status,
        current_source_event_version=final.source_event_version,
        proposal_id=final.proposal_id,
        proposal_record_created=True,
        suitability_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        created_at_utc=RECORDED_AT,
        updated_at_utc=final.occurred_at_utc,
        outcomes=tuple(outcomes),
    )


def _rejected_history() -> AdviseProposalRealizationHistory:
    outcome = AdviseProposalRealizationOutcome(
        outcome_id="ipro_rejected_001",
        source_event_version=1,
        status=AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
        reason_code="idea_intake_rejected_before_work",
        occurred_at_utc=RECORDED_AT,
        review_work_id=None,
        proposal_id=None,
        terminal=True,
    )
    return AdviseProposalRealizationHistory(
        realization_id="ipr_001",
        intake_id="ipi_001",
        review_work_id=None,
        review_work_status=None,
        source_authority="lotus-idea",
        realization_authority="lotus-advise",
        tenant_id="tenant-sg",
        legal_entity_code="SGPB",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id="idea-downstream-001",
        conversion_intent_id="conversion-advise_proposal-001",
        source_evidence_fingerprint="sha256:downstream-evidence",
        current_status=AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
        current_source_event_version=1,
        proposal_id=None,
        proposal_record_created=False,
        suitability_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        created_at_utc=RECORDED_AT,
        updated_at_utc=RECORDED_AT,
        outcomes=(outcome,),
    )
