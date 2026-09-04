"""Idea reconciles the exact Manage owner history - never transport success.

Mirrors the certified Advise consumer (idea#1215) against manage#660's shipped
contract: eligibility needs a terminal owner submission with a receipt, the
caller scope is checked before the owner is called, identity drift and version
regressions fail closed, and reopened reviews (the owner's non-absorbing
machine) reconcile as ordinary appends.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest

from app.application.downstream_realization import (
    RealizeConversionIntentCommand,
    submit_conversion_intent_to_downstream,
)
from app.application.manage_realization_reconciliation import (
    ManageRealizationAccessScopeDenied,
    ManageRealizationReconciliationStatus,
    ReconcileManageRealizationCommand,
    _history_identity_blocker,
    _submission_eligibility_blocker,
    reconcile_manage_realization_history,
)
from app.domain import (
    ConversionTarget,
    InMemoryIdeaRepository,
    ManageActionRealizationEvent,
    ManageActionRealizationEventType,
    ManageActionRealizationHistory,
    ManageActionRealizationStatus,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.domain.persistence_manage_realization import manage_realization_submission_blocker
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationOutcome,
    DownstreamRealizationReadError,
)
from tests.unit.test_downstream_realization_application import (
    CapturingManageClient,
    repository_with_conversion,
)


RECORDED_AT = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)
AUTHORIZED_SCOPE = QueueAccessScopeFilter(
    tenant_id="tenant-sg",
    book_id="book-private-bank-sg",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-redacted",
)


@dataclass
class StubManageReader:
    history: ManageActionRealizationHistory
    calls: int = 0

    def load_action_realization(
        self,
        *,
        intake_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> ManageActionRealizationHistory:
        self.calls += 1
        assert intake_id == "iai_001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        return self.history


@dataclass
class RaisingManageReader:
    calls: int = 0

    def load_action_realization(self, **kwargs: object) -> ManageActionRealizationHistory:
        self.calls += 1
        raise DownstreamRealizationReadError("manage is down")


def test_reconcile_manage_history_persists_append_only_owner_evidence() -> None:
    """Accept, replay, then progress through the owner's REOPENED review -
    the append that a terminal-status consumer would wrongly refuse."""

    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(_history(version=2))

    accepted = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )
    replayed = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )
    reader.history = _history(version=3)
    reopened = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )

    assert accepted.status is ManageRealizationReconciliationStatus.ACCEPTED
    assert accepted.appended_event_count == 2
    assert replayed.status is ManageRealizationReconciliationStatus.REPLAYED
    assert replayed.appended_event_count == 0
    assert reopened.status is ManageRealizationReconciliationStatus.ACCEPTED
    assert reopened.appended_event_count == 1
    assert reopened.history is not None
    assert reopened.history.status is ManageActionRealizationStatus.PENDING_REVIEW
    assert reopened.grants_rebalance_execution_authority is False
    assert reopened.grants_order_authority is False
    assert reopened.grants_client_publication_authority is False
    persisted = repository.manage_realization_history_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.source_event_version == 3


def test_reconcile_manage_history_fails_closed_on_owner_identity_drift() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(replace(_history(version=2), portfolio_id="PB_OTHER"))

    result = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )

    assert result.status is ManageRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "manage_realization_scope_conflict"
    assert repository.manage_realization_history_by_support_reference(support_reference) is None


def test_reconcile_manage_history_denies_scope_before_owner_call() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(_history(version=2))

    with pytest.raises(ManageRealizationAccessScopeDenied):
        reconcile_manage_realization_history(
            replace(
                _command(support_reference),
                access_scope_filter=replace(AUTHORIZED_SCOPE, portfolio_id=("PB_OTHER",)),
            ),
            repository=repository,
            manage_reader=reader,
        )

    assert reader.calls == 0


def test_reconcile_manage_history_holds_owner_unavailability_without_evidence() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    unavailable = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=RaisingManageReader(),
    )
    unconfigured = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=None,
    )

    assert unavailable.status is ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE
    assert unavailable.blocker == "manage_realization_owner_unavailable"
    assert unconfigured.status is ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE
    assert unconfigured.blocker == "manage_realization_reader_not_configured"
    assert repository.manage_realization_history_by_support_reference(support_reference) is None


def test_reconcile_manage_history_treats_invalid_owner_bodies_as_conflicts() -> None:
    @dataclass
    class InvalidReader:
        def load_action_realization(self, **kwargs: object) -> ManageActionRealizationHistory:
            raise ValueError("events must be an array")

    repository, support_reference = _repository_with_accepted_submission()
    result = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=InvalidReader(),
    )

    assert result.status is ManageRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "manage_realization_history_invalid"


def test_reconcile_manage_history_reports_unknown_submissions() -> None:
    repository, _support_reference = _repository_with_accepted_submission()

    result = reconcile_manage_realization_history(
        _command("downstream-submission-ffffffffffffffffffffffff"),
        repository=repository,
        manage_reader=StubManageReader(_history(version=2)),
    )

    assert result.status is ManageRealizationReconciliationStatus.NOT_FOUND


def test_reconcile_manage_history_refuses_prefix_rewrites() -> None:
    """A rewritten event two under a higher version is corruption, not
    progress: the persisted prefix is immutable."""

    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(_history(version=2))
    reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )

    reader.history = replace(
        _history(version=3),
        events=(
            _event(1),
            replace(_event(2), event_id="imae_rewritten"),
            _event(3),
        ),
    )
    result = reconcile_manage_realization_history(
        _command(support_reference),
        repository=repository,
        manage_reader=reader,
    )

    assert result.status is ManageRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "manage_realization_history_conflict"
    persisted = repository.manage_realization_history_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.source_event_version == 2


def test_submission_eligibility_requires_terminal_manage_ownership() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    submission = repository.downstream_submission_by_support_reference(support_reference)
    assert submission is not None

    assert _submission_eligibility_blocker(submission) is None
    assert (
        _submission_eligibility_blocker(
            replace(submission, target=ConversionTarget.ADVISE_PROPOSAL)
        )
        == "manage_realization_requires_manage_target"
    )
    receipt = submission.owner_receipt
    assert receipt is not None
    assert (
        _submission_eligibility_blocker(
            replace(
                submission,
                source_authority=SourceSystem.LOTUS_ADVISE,
                owner_receipt=replace(receipt, owner_authority=SourceSystem.LOTUS_ADVISE),
            )
        )
        == "manage_realization_requires_manage_authority"
    )
    assert (
        _submission_eligibility_blocker(replace(submission, owner_receipt=None))
        == "manage_realization_owner_receipt_missing"
    )


def test_history_identity_blocker_names_each_drift() -> None:
    scope = ReviewAccessScope(
        tenant_id="tenant-sg",
        book_id="book-private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-redacted",
    )

    def blocker(history: ManageActionRealizationHistory) -> str | None:
        return _history_identity_blocker(
            history,
            access_scope=scope,
            candidate_id="idea-downstream-001",
            conversion_intent_id="conversion-manage_review-001",
            intake_id="iai_001",
        )

    assert blocker(_history(version=2)) is None
    assert (
        blocker(replace(_history(version=2), intake_id="iai_002"))
        == "manage_realization_intake_conflict"
    )
    assert (
        blocker(replace(_history(version=2), idea_candidate_id="idea-other"))
        == "manage_realization_candidate_conflict"
    )
    assert (
        blocker(replace(_history(version=2), conversion_intent_id="conversion-other"))
        == "manage_realization_conversion_intent_conflict"
    )


def test_persistence_blocker_binds_the_receipt_to_the_owner_history() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    submission = repository.downstream_submission_by_support_reference(support_reference)
    assert submission is not None
    history = _history(version=2)

    assert manage_realization_submission_blocker(submission, history) is None
    receipt = submission.owner_receipt
    assert receipt is not None
    # The receipt binds the durable action identity: a receipt naming a
    # different management action than the history refuses persistence.
    drifted = replace(
        submission,
        owner_receipt=replace(
            receipt,
            owner_realization_id="ima_002",
            owner_work_id="ima_002",
        ),
    )
    assert (
        manage_realization_submission_blocker(drifted, history)
        == "manage_realization_owner_receipt_conflict"
    )
    regressed = replace(submission, owner_receipt=replace(receipt, source_event_version=9))
    assert (
        manage_realization_submission_blocker(regressed, history)
        == "manage_realization_history_regressed_below_receipt"
    )


def _repository_with_accepted_submission() -> tuple[InMemoryIdeaRepository, str]:
    repository = repository_with_conversion(ConversionTarget.MANAGE_REVIEW)
    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-manage_review-001",
            idempotency_key="submission-manage-owner-history-001",
            actor_subject="advisor-redacted",
            access_scope_filter=AUTHORIZED_SCOPE,
            submitted_at_utc=RECORDED_AT,
        ),
        repository=repository,
        advise_client=None,
        manage_client=CapturingManageClient(
            DownstreamRealizationOutcome.accepted_by_downstream(
                DownstreamOwnerReceipt(
                    owner_authority=SourceSystem.LOTUS_MANAGE,
                    owner_request_id="iai_001",
                    owner_realization_id="ima_001",
                    owner_work_id="ima_001",
                    source_event_version=1,
                    source_evidence_fingerprint="sha256:aabbccddeeff",
                )
            )
        ),
    )
    assert result.support_reference is not None
    return repository, result.support_reference


def _command(support_reference: str) -> ReconcileManageRealizationCommand:
    return ReconcileManageRealizationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE,
        correlation_id="corr-manage-history",
        trace_id="trace-manage-history",
    )


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
