from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.advise_realization_reconciliation import (
    _request_context_id,
    _require_reconciliation_caller,
    _response,
)

from app.application.advise_realization_reconciliation import (
    AdviseRealizationAccessScopeDenied,
    AdviseRealizationReconciliationResult,
    AdviseRealizationReconciliationStatus,
    ReconcileAdviseRealizationCommand,
    _history_identity_blocker,
    _submission_eligibility_blocker,
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
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    InMemoryIdeaRepository,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.domain.persistence_advise_realization import advise_realization_submission_blocker
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationReadError,
    DownstreamRealizationOutcome,
)
from app.security.caller_context import (
    CallerContext,
    CallerEntitlementScope,
    PermissionDeniedError,
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


def test_reconcile_fails_closed_when_submission_or_owner_reader_is_missing() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    missing = reconcile_advise_realization_history(
        _command("downstream-submission-000000000000000000000000"),
        repository=repository,
        advise_reader=None,
    )
    unavailable = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=None,
    )

    assert missing.status is AdviseRealizationReconciliationStatus.NOT_FOUND
    assert unavailable.status is AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE
    assert unavailable.blocker == "advise_realization_reader_not_configured"


def test_reconcile_rejects_malformed_authoritative_history() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    class MalformedReader:
        def load_proposal_realization(self, **_kwargs: object) -> AdviseProposalRealizationHistory:
            raise ValueError("owner payload is malformed")

    result = reconcile_advise_realization_history(
        _command(support_reference),
        repository=repository,
        advise_reader=MalformedReader(),
    )

    assert result.status is AdviseRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "advise_realization_history_invalid"


def test_advise_reconciliation_eligibility_requires_terminal_advise_receipt() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    submission = repository.downstream_submission_by_support_reference(support_reference)
    assert submission is not None
    assert submission.owner_receipt is not None

    cases = (
        (
            replace(
                submission,
                resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
            ),
            "advise_realization_requires_conversion_intent_submission",
        ),
        (
            replace(submission, target=ConversionTarget.MANAGE_REVIEW),
            "advise_realization_requires_advise_target",
        ),
        (
            replace(
                submission,
                source_authority=SourceSystem.LOTUS_MANAGE,
                owner_receipt=replace(
                    submission.owner_receipt,
                    owner_authority=SourceSystem.LOTUS_MANAGE,
                ),
            ),
            "advise_realization_requires_advise_authority",
        ),
        (
            replace(
                submission,
                status=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
                downstream_failure_reason="owner_outcome_uncertain",
                owner_receipt=None,
            ),
            "advise_realization_requires_terminal_owner_submission",
        ),
        (
            replace(submission, owner_receipt=None),
            "advise_realization_owner_receipt_missing",
        ),
    )

    for malformed, expected in cases:
        assert _submission_eligibility_blocker(malformed) == expected
        assert advise_realization_submission_blocker(malformed, _history(version=2)) == expected
    assert _submission_eligibility_blocker(submission) is None

    assert submission.owner_receipt is not None
    conflicting_receipt = replace(
        submission.owner_receipt,
        owner_request_id="ipi_different",
    )
    assert (
        advise_realization_submission_blocker(
            replace(submission, owner_receipt=conflicting_receipt),
            _history(version=2),
        )
        == "advise_realization_owner_receipt_conflict"
    )
    regressed_receipt = replace(submission.owner_receipt, source_event_version=3)
    assert (
        advise_realization_submission_blocker(
            replace(submission, owner_receipt=regressed_receipt),
            _history(version=2),
        )
        == "advise_realization_history_regressed_below_receipt"
    )
    assert advise_realization_submission_blocker(submission, _history(version=2)) is None


def test_in_memory_advise_history_repository_fails_closed_on_missing_or_conflicting_source() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    history = _history(version=2)

    missing = repository.persist_advise_realization_history(
        support_reference="downstream-submission-000000000000000000000000",
        history=history,
    )
    conflict = repository.persist_advise_realization_history(
        support_reference=support_reference,
        history=replace(history, intake_id="ipi_different"),
    )

    assert missing.decision.value == "not_found"
    assert missing.blocker == "downstream_submission_not_found"
    assert conflict.decision.value == "conflict"
    assert conflict.blocker == "advise_realization_owner_receipt_conflict"
    with pytest.raises(ValueError, match="support_reference is required"):
        repository.advise_realization_history_by_support_reference(" ")


def test_advise_reconciliation_identity_check_names_exact_evidence_drift() -> None:
    history = _history(version=2)
    scope = ReviewAccessScope(
        tenant_id="tenant-sg",
        book_id="book-private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-redacted",
    )
    cases = (
        (replace(history, tenant_id="different"), "advise_realization_scope_conflict"),
        (
            replace(history, idea_candidate_id="different"),
            "advise_realization_candidate_conflict",
        ),
        (
            replace(history, conversion_intent_id="different"),
            "advise_realization_conversion_intent_conflict",
        ),
        (
            replace(history, source_evidence_fingerprint="sha256:different"),
            "advise_realization_evidence_conflict",
        ),
    )

    for changed, blocker in cases:
        assert (
            _history_identity_blocker(
                changed,
                access_scope=scope,
                candidate_id="idea-downstream-001",
                conversion_intent_id="conversion-advise_proposal-001",
                evidence_fingerprint="sha256:downstream-evidence",
            )
            == blocker
        )
    assert (
        _history_identity_blocker(
            history,
            access_scope=scope,
            candidate_id="idea-downstream-001",
            conversion_intent_id="conversion-advise_proposal-001",
            evidence_fingerprint="sha256:downstream-evidence",
        )
        is None
    )


@pytest.mark.parametrize("field_name", ["support_reference", "actor_subject"])
def test_reconcile_command_requires_auditable_identity(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} is required"):
        ReconcileAdviseRealizationCommand(
            support_reference=(
                " "
                if field_name == "support_reference"
                else "downstream-submission-000000000000000000000000"
            ),
            actor_subject=" " if field_name == "actor_subject" else "operator-redacted",
            access_scope_filter=AUTHORIZED_SCOPE,
        )


@pytest.mark.parametrize(
    ("reconciliation_status", "blocker", "http_status", "code"),
    [
        (
            AdviseRealizationReconciliationStatus.NOT_FOUND,
            None,
            404,
            "downstream_submission_not_found",
        ),
        (
            AdviseRealizationReconciliationStatus.NOT_ELIGIBLE,
            "advise_realization_requires_terminal_owner_submission",
            409,
            "advise_realization_requires_terminal_owner_submission",
        ),
        (
            AdviseRealizationReconciliationStatus.CONFLICT,
            None,
            409,
            "advise_realization_reconciliation_conflict",
        ),
        (
            AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            None,
            503,
            "advise_realization_owner_unavailable",
        ),
    ],
)
def test_advise_reconciliation_api_maps_failure_posture_without_false_success(
    reconciliation_status: AdviseRealizationReconciliationStatus,
    blocker: str | None,
    http_status: int,
    code: str,
) -> None:
    response = _response(
        AdviseRealizationReconciliationResult(
            status=reconciliation_status,
            history=None,
            blocker=blocker,
        ),
        durable_storage_backed=True,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == http_status
    assert json.loads(bytes(response.body))["code"] == code


def test_advise_reconciliation_api_requires_capability_and_complete_scope() -> None:
    complete_scope = CallerEntitlementScope(
        tenant_ids=("tenant-sg",),
        book_ids=("book-private-bank-sg",),
        portfolio_ids=("PB_SG_GLOBAL_BAL_001",),
        client_ids=("client-redacted",),
    )
    without_capability = CallerContext(
        subject="operator-redacted",
        entitlement_scope=complete_scope,
    )
    incomplete_scope = CallerContext(
        subject="operator-redacted",
        capabilities=frozenset({"idea.downstream-realization.reconcile"}),
        entitlement_scope=replace(complete_scope, client_ids=()),
    )
    authorized = replace(
        incomplete_scope,
        entitlement_scope=complete_scope,
    )

    with pytest.raises(PermissionDeniedError):
        _require_reconciliation_caller(without_capability)
    with pytest.raises(PermissionDeniedError):
        _require_reconciliation_caller(incomplete_scope)
    _require_reconciliation_caller(authorized)


def test_advise_reconciliation_request_context_ignores_absent_values() -> None:
    request = cast(
        Request,
        SimpleNamespace(state=SimpleNamespace(correlation_id="corr-001", trace_id=None)),
    )

    assert _request_context_id(request, "correlation_id") == "corr-001"
    assert _request_context_id(request, "trace_id") is None


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
