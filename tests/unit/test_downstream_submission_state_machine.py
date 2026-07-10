from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionAuditAction,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    SourceSystem,
    create_downstream_submission_claim,
    downstream_submission_support_reference,
    evaluate_downstream_submission_claim,
    finalize_downstream_submission,
    reconcile_downstream_submission,
)


CLAIMED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_claim_is_lease_fenced_audited_and_opaque() -> None:
    record = _claim()

    assert record.status is DownstreamSubmissionPosture.IN_FLIGHT
    assert record.support_reference == downstream_submission_support_reference(
        "downstream-secret-key"
    )
    assert "downstream-secret-key" not in record.support_reference
    assert record.attempt_count == 1
    assert record.audit_history[0].action is DownstreamSubmissionAuditAction.CLAIMED
    assert record.audit_history[0].current_posture is DownstreamSubmissionPosture.IN_FLIGHT


def test_claim_decision_never_reissues_uncertain_work() -> None:
    record = _claim()

    assert (
        evaluate_downstream_submission_claim(record, request_fingerprint="fingerprint-a")
        is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
    )
    assert (
        evaluate_downstream_submission_claim(record, request_fingerprint="fingerprint-b")
        is DownstreamSubmissionClaimDecision.CONFLICT
    )
    accepted = finalize_downstream_submission(
        record,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    ).record
    assert accepted is not None
    assert (
        evaluate_downstream_submission_claim(accepted, request_fingerprint="fingerprint-a")
        is DownstreamSubmissionClaimDecision.REPLAYED
    )


def test_finalize_requires_the_claim_lease_and_preserves_audit() -> None:
    record = _claim()

    conflict = finalize_downstream_submission(
        record,
        lease_owner="competing-worker",
        lease_attempt_id="attempt-002",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    )
    accepted = finalize_downstream_submission(
        record,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_rejected",
    )

    assert conflict.decision is DownstreamSubmissionMutationDecision.LEASE_CONFLICT
    assert accepted.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert accepted.record is not None
    assert accepted.record.status is DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM
    assert accepted.record.audit_history[-1].action is DownstreamSubmissionAuditAction.FINALIZED


def test_unknown_outcome_requires_explicit_reconciliation() -> None:
    uncertain = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    ).record
    assert uncertain is not None

    reconciled = reconcile_downstream_submission(
        uncertain,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="downstream_receipt_verified",
        change_reference="CHG-334-001",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )

    assert reconciled.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert reconciled.record is not None
    assert reconciled.record.status is DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM
    assert reconciled.record.audit_history[-1].action is DownstreamSubmissionAuditAction.RECONCILED
    assert reconciled.record.audit_history[-1].change_reference == "CHG-334-001"


def test_operator_can_quarantine_but_cannot_rewrite_terminal_history() -> None:
    uncertain = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_outcome_unknown",
    ).record
    assert uncertain is not None
    quarantined = reconcile_downstream_submission(
        uncertain,
        resolution=DownstreamSubmissionResolution.QUARANTINED,
        actor_subject="operations-user",
        reason="receipt_cannot_be_verified",
        change_reference="INC-334-001",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
    ).record
    assert quarantined is not None

    repeated = reconcile_downstream_submission(
        quarantined,
        resolution=DownstreamSubmissionResolution.REJECTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="late_override",
        change_reference="INC-334-002",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=6),
    )

    assert quarantined.status is DownstreamSubmissionPosture.QUARANTINED
    assert quarantined.audit_history[-1].action is DownstreamSubmissionAuditAction.QUARANTINED
    assert repeated.decision is DownstreamSubmissionMutationDecision.INVALID_STATE


def test_reconciliation_change_reference_is_replay_safe_and_conflict_aware() -> None:
    uncertain = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    ).record
    assert uncertain is not None
    accepted = reconcile_downstream_submission(
        uncertain,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="downstream_receipt_verified",
        change_reference="INC-334-003",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )
    assert accepted.record is not None

    replayed = reconcile_downstream_submission(
        accepted.record,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="downstream_receipt_verified",
        change_reference="INC-334-003",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=6),
    )
    conflict = reconcile_downstream_submission(
        accepted.record,
        resolution=DownstreamSubmissionResolution.REJECTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="downstream_receipt_rejected",
        change_reference="INC-334-003",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=6),
    )

    assert replayed.decision is DownstreamSubmissionMutationDecision.REPLAYED
    assert conflict.decision is DownstreamSubmissionMutationDecision.INVALID_STATE
    assert conflict.blocker == "downstream_submission_change_reference_conflict"


def test_claim_rejects_partial_or_invalid_lease() -> None:
    with pytest.raises(ValueError, match="lease_expires_at_utc must be after"):
        _claim(lease_expires_at_utc=CLAIMED_AT)

    with pytest.raises(ValueError, match="support_reference must match"):
        replace(
            _claim(),
            support_reference="downstream-submission-000000000000000000000000",
        )


def _claim(
    *,
    lease_expires_at_utc: datetime = CLAIMED_AT + timedelta(minutes=5),
) -> DownstreamSubmissionRecord:
    return create_downstream_submission_claim(
        idempotency_key="downstream-secret-key",
        request_fingerprint="fingerprint-a",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject="advisor-redacted",
        claimed_at_utc=CLAIMED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        lease_expires_at_utc=lease_expires_at_utc,
        correlation_id="corr-334",
        trace_id="trace-334",
    )
