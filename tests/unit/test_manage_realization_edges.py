"""Fail-closed edges of the Manage realization consumer.

Every refusal the happy-path suites step over: blank identities, non-UTC
clocks, missing source resources, vanished submissions, empty caller scope,
and the API problem responses for each terminal status.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from app.ports.idea_repository import DownstreamSubmissionRepository
from datetime import datetime, timedelta, timezone

import pytest

from app.application.manage_realization_reconciliation import (
    ManageRealizationAccessScopeDenied,
    ManageRealizationReconciliationResult,
    ManageRealizationReconciliationStatus,
    ReconcileManageRealizationCommand,
    reconcile_manage_realization_history,
)
from app.api.manage_realization_reconciliation import _response
from app.domain import (
    ConversionTarget,
    DownstreamSubmissionResourceType,
    ManageRealizationHistoryMutationDecision,
    ManageRealizationHistoryMutationResult,
    QueueAccessScopeFilter,
    SourceSystem,
)
from app.domain.persistence_manage_realization import manage_realization_submission_blocker
from tests.unit.test_manage_realization_reconciliation import (
    AUTHORIZED_SCOPE,
    RECORDED_AT,
    StubManageReader,
    _command,
    _event,
    _history,
    _repository_with_accepted_submission,
)


def test_event_and_history_refuse_blank_and_untimed_identities() -> None:
    with pytest.raises(ValueError, match="source_event_version must be positive"):
        replace(_event(1), source_event_version=0)
    with pytest.raises(ValueError, match="event_id is required"):
        replace(_event(1), event_id="  ")
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_event(1), occurred_at_utc=datetime(2026, 9, 3, 10, 0))
    with pytest.raises(ValueError, match="must be UTC"):
        replace(
            _event(1),
            occurred_at_utc=datetime(2026, 9, 3, 10, 0, tzinfo=timezone(timedelta(hours=8))),
        )
    with pytest.raises(ValueError, match="source_event_version must be positive"):
        replace(_history(version=1), source_event_version=0)
    with pytest.raises(ValueError, match="events are required"):
        replace(_history(version=1), events=())


def test_reconcile_command_requires_identifying_text() -> None:
    with pytest.raises(ValueError, match="support_reference is required"):
        ReconcileManageRealizationCommand(
            support_reference="  ",
            actor_subject="operator",
            access_scope_filter=AUTHORIZED_SCOPE,
        )


def test_empty_caller_scope_is_denied_before_any_owner_io() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(_history(version=2))

    with pytest.raises(ManageRealizationAccessScopeDenied):
        reconcile_manage_realization_history(
            replace(_command(support_reference), access_scope_filter=QueueAccessScopeFilter()),
            repository=repository,
            manage_reader=reader,
        )

    assert reader.calls == 0


def test_non_terminal_submissions_are_not_eligible() -> None:
    """A submission still in flight - claimed, not yet finalized with an
    owner outcome - has no owner history to reconcile."""

    from datetime import timedelta as _timedelta

    from app.domain import create_downstream_submission_claim

    repository, _support_reference = _repository_with_accepted_submission()
    claim = create_downstream_submission_claim(
        idempotency_key="submission-manage-in-flight-001",
        request_fingerprint="sha256:manage-in-flight",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-manage_review-001",
        target=ConversionTarget.MANAGE_REVIEW,
        source_authority=SourceSystem.LOTUS_MANAGE,
        actor_subject="advisor-redacted",
        claimed_at_utc=RECORDED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-manage-in-flight",
        lease_expires_at_utc=RECORDED_AT + _timedelta(minutes=5),
    )
    repository.claim_downstream_submission(claim)

    result = reconcile_manage_realization_history(
        _command(claim.support_reference),
        repository=repository,
        manage_reader=StubManageReader(_history(version=2)),
    )

    assert result.status is ManageRealizationReconciliationStatus.NOT_ELIGIBLE
    assert result.blocker == "manage_realization_requires_terminal_owner_submission"


def test_missing_source_resources_conflict_before_owner_io() -> None:
    repository, support_reference = _repository_with_accepted_submission()
    reader = StubManageReader(_history(version=2))

    class _IntentlessRepository:
        def __getattr__(self, name: str) -> object:
            return getattr(repository, name)

        def conversion_intent_by_id(self, conversion_intent_id: str) -> None:
            return None

    result = reconcile_manage_realization_history(
        _command(support_reference),
        repository=cast("DownstreamSubmissionRepository", _IntentlessRepository()),
        manage_reader=reader,
    )

    assert result.status is ManageRealizationReconciliationStatus.CONFLICT
    assert result.blocker == "manage_realization_source_resource_missing"
    assert reader.calls == 0


def test_a_submission_vanishing_between_read_and_persist_reports_not_found() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    class _VanishingRepository:
        def __getattr__(self, name: str) -> object:
            return getattr(repository, name)

        def persist_manage_realization_history(
            self, *, support_reference: str, history: object
        ) -> ManageRealizationHistoryMutationResult:
            return ManageRealizationHistoryMutationResult(
                decision=ManageRealizationHistoryMutationDecision.NOT_FOUND,
                history=None,
                blocker="downstream_submission_not_found",
            )

    result = reconcile_manage_realization_history(
        _command(support_reference),
        repository=cast("DownstreamSubmissionRepository", _VanishingRepository()),
        manage_reader=StubManageReader(_history(version=2)),
    )

    assert result.status is ManageRealizationReconciliationStatus.NOT_FOUND


def test_in_memory_persistence_fails_closed_on_unknown_and_blocked_submissions() -> None:
    repository, support_reference = _repository_with_accepted_submission()

    missing = repository.persist_manage_realization_history(
        support_reference="downstream-submission-eeeeeeeeeeeeeeeeeeeeeeee",
        history=_history(version=2),
    )
    assert missing.decision is ManageRealizationHistoryMutationDecision.NOT_FOUND
    assert missing.blocker == "downstream_submission_not_found"

    blocked = repository.persist_manage_realization_history(
        support_reference=support_reference,
        history=replace(_history(version=2), intake_id="iai_other"),
    )
    assert blocked.decision is ManageRealizationHistoryMutationDecision.CONFLICT
    assert blocked.blocker == "manage_realization_owner_receipt_conflict"

    with pytest.raises(ValueError, match="support_reference is required"):
        repository.manage_realization_history_by_support_reference("  ")


def test_persistence_blocker_names_every_ineligible_submission_shape() -> None:
    from datetime import timedelta as _timedelta

    from app.domain import create_downstream_submission_claim

    repository, support_reference = _repository_with_accepted_submission()
    submission = repository.downstream_submission_by_support_reference(support_reference)
    assert submission is not None
    history = _history(version=2)

    # The eligibility gate (use case) and the persistence blocker both refuse
    # a non-conversion submission - the same fact checked at both boundaries.
    from app.application.manage_realization_reconciliation import (
        _submission_eligibility_blocker,
    )

    assert (
        _submission_eligibility_blocker(
            replace(
                submission,
                resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
            )
        )
        == "manage_realization_requires_conversion_intent_submission"
    )
    in_flight = create_downstream_submission_claim(
        idempotency_key="submission-manage-blocker-in-flight",
        request_fingerprint="sha256:manage-blocker-in-flight",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-manage_review-001",
        target=ConversionTarget.MANAGE_REVIEW,
        source_authority=SourceSystem.LOTUS_MANAGE,
        actor_subject="advisor-redacted",
        claimed_at_utc=RECORDED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-manage-blocker-in-flight",
        lease_expires_at_utc=RECORDED_AT + _timedelta(minutes=5),
    )
    assert (
        manage_realization_submission_blocker(in_flight, history)
        == "manage_realization_requires_terminal_owner_submission"
    )

    assert (
        manage_realization_submission_blocker(
            replace(
                submission,
                resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
            ),
            history,
        )
        == "manage_realization_requires_conversion_intent_submission"
    )
    assert (
        manage_realization_submission_blocker(
            replace(submission, target=ConversionTarget.ADVISE_PROPOSAL),
            history,
        )
        == "manage_realization_requires_manage_target"
    )
    receipt = submission.owner_receipt
    assert receipt is not None
    assert (
        manage_realization_submission_blocker(
            replace(
                submission,
                source_authority=SourceSystem.LOTUS_ADVISE,
                owner_receipt=replace(receipt, owner_authority=SourceSystem.LOTUS_ADVISE),
            ),
            history,
        )
        == "manage_realization_requires_manage_authority"
    )
    assert (
        manage_realization_submission_blocker(
            replace(submission, owner_receipt=None),
            history,
        )
        == "manage_realization_owner_receipt_missing"
    )


def test_api_response_maps_every_terminal_status_to_its_problem() -> None:
    from fastapi.responses import JSONResponse

    def _problem(result: ManageRealizationReconciliationResult) -> JSONResponse:
        response = _response(result, durable_storage_backed=True)
        assert isinstance(response, JSONResponse)
        return response

    not_found = _problem(
        ManageRealizationReconciliationResult(
            status=ManageRealizationReconciliationStatus.NOT_FOUND,
            history=None,
        )
    )
    assert not_found.status_code == 404

    conflict = _problem(
        ManageRealizationReconciliationResult(
            status=ManageRealizationReconciliationStatus.CONFLICT,
            history=None,
            blocker="manage_realization_scope_conflict",
        )
    )
    assert conflict.status_code == 409

    unavailable = _problem(
        ManageRealizationReconciliationResult(
            status=ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            history=None,
            blocker="manage_realization_owner_unavailable",
        )
    )
    assert unavailable.status_code == 503
