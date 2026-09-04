from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionAuditAction,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    ReportMaterializationReceiptEvidence,
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


def test_rejected_submission_preserves_authoritative_owner_receipt() -> None:
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_ADVISE,
        owner_request_id="ipi_rejected_001",
        owner_realization_id="ipr_rejected_001",
        owner_work_id=None,
        source_event_version=1,
        source_evidence_fingerprint="sha256:evidence-redacted",
    )

    result = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_rejected",
        owner_receipt=receipt,
    )

    assert result.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert result.record is not None
    assert result.record.owner_receipt == receipt


def test_owner_receipt_and_submission_reject_contradictory_owner_evidence() -> None:
    with pytest.raises(ValueError, match="source_event_version must be positive"):
        _owner_receipt(source_event_version=0)
    with pytest.raises(ValueError, match="must use sha256"):
        _owner_receipt(source_evidence_fingerprint="md5:unsafe")

    receipt = _owner_receipt()
    with pytest.raises(ValueError, match="requires a terminal downstream posture"):
        finalize_downstream_submission(
            _claim(),
            lease_owner="downstream-submission",
            lease_attempt_id="attempt-001",
            posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
            failure_reason="owner_outcome_uncertain",
            owner_receipt=receipt,
        )
    with pytest.raises(ValueError, match="authority must match"):
        finalize_downstream_submission(
            _claim(),
            lease_owner="downstream-submission",
            lease_attempt_id="attempt-001",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
            owner_receipt=replace(receipt, owner_authority=SourceSystem.LOTUS_MANAGE),
        )

    accepted = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        owner_receipt=receipt,
    ).record
    assert accepted is not None
    with pytest.raises(ValueError, match="requires a terminal downstream posture"):
        replace(accepted, status=DownstreamSubmissionPosture.IN_FLIGHT)
    with pytest.raises(ValueError, match="authority must match"):
        replace(
            accepted,
            owner_receipt=replace(receipt, owner_authority=SourceSystem.LOTUS_MANAGE),
        )


def test_report_owner_receipt_rejects_authority_or_supportability_inflation() -> None:
    evidence = ReportMaterializationReceiptEvidence(
        status="data_ready",
        materialization_status="data_ready",
        status_url="/reports/jobs/report-job-001",
        report_evidence_pack_id="report-pack-001",
        conversion_intent_id="conversion-report-001",
        candidate_id="candidate-report-001",
        evidence_packet_id="evidence-packet-001",
        creates_report_job=True,
        creates_rendered_output=False,
        creates_archive_record=False,
        render_job_id=None,
        archive_document_id=None,
        supportability_status="not_certified",
        remaining_blockers=(
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ),
    )
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_REPORT,
        owner_request_id="report-request-001",
        owner_realization_id="report-job-001",
        owner_work_id=None,
        source_event_version=None,
        source_evidence_fingerprint="sha256:report-evidence",
        report_materialization=evidence,
    )

    assert receipt.report_materialization == evidence
    with pytest.raises(ValueError, match="must remain not_certified"):
        replace(evidence, supportability_status="supported")
    with pytest.raises(ValueError, match="required supportability blockers"):
        replace(evidence, remaining_blockers=("client_publication_authority_blocked",))
    with pytest.raises(ValueError, match="status fields must agree"):
        replace(evidence, materialization_status="failed")
    with pytest.raises(ValueError, match="must create a report job"):
        replace(evidence, creates_report_job=False)
    with pytest.raises(ValueError, match="render creation posture"):
        replace(evidence, creates_rendered_output=True)
    with pytest.raises(ValueError, match="archive creation posture"):
        replace(evidence, creates_archive_record=True)
    with pytest.raises(ValueError, match="archive record requires rendered output"):
        replace(evidence, creates_archive_record=True, archive_document_id="archive-001")
    with pytest.raises(ValueError, match="remaining_blockers is required"):
        replace(evidence, remaining_blockers=())
    with pytest.raises(ValueError, match="status_url must match"):
        replace(receipt, owner_realization_id="report-job-drift")
    with pytest.raises(ValueError, match="has no source event version"):
        replace(receipt, source_event_version=1)
    with pytest.raises(ValueError, match="requires materialization evidence"):
        replace(receipt, report_materialization=None)
    with pytest.raises(ValueError, match="uses owner_realization_id"):
        replace(receipt, owner_work_id="report-work-001")
    with pytest.raises(ValueError, match="evented owner receipt requires"):
        replace(
            receipt,
            owner_authority=SourceSystem.LOTUS_ADVISE,
            report_materialization=None,
        )
    with pytest.raises(ValueError, match="requires lotus-report authority"):
        replace(
            receipt,
            owner_authority=SourceSystem.LOTUS_ADVISE,
            source_event_version=1,
        )


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


def test_reconciliation_can_bind_recovered_owner_receipt_with_exact_replay() -> None:
    uncertain = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    ).record
    assert uncertain is not None
    receipt = _owner_receipt()

    accepted = reconcile_downstream_submission(
        uncertain,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="authoritative_owner_history_recovered",
        change_reference="owner-recovery-v1",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
        owner_receipt=receipt,
    )
    assert accepted.record is not None
    replayed = reconcile_downstream_submission(
        accepted.record,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="authoritative_owner_history_recovered",
        change_reference="owner-recovery-v1",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=6),
        owner_receipt=receipt,
    )
    conflicting_receipt = reconcile_downstream_submission(
        accepted.record,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="operations-user",
        reason="authoritative_owner_history_recovered",
        change_reference="owner-recovery-v1",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=6),
        owner_receipt=replace(receipt, owner_request_id="ipi_conflict"),
    )

    assert accepted.record.owner_receipt == receipt
    assert replayed.decision is DownstreamSubmissionMutationDecision.REPLAYED
    assert conflicting_receipt.decision is DownstreamSubmissionMutationDecision.INVALID_STATE
    assert conflicting_receipt.blocker == "downstream_submission_change_reference_conflict"


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


def test_submission_record_rejects_non_recoverable_state_shapes() -> None:
    claim = _claim()

    with pytest.raises(ValueError, match="attempt_count must be positive"):
        replace(claim, attempt_count=0)
    with pytest.raises(ValueError, match="audit_history is required"):
        replace(claim, audit_history=())
    with pytest.raises(ValueError, match="requires a complete lease"):
        replace(claim, lease_owner=None)
    with pytest.raises(ValueError, match="requires a failure reason"):
        replace(
            claim,
            status=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            lease_owner=None,
            lease_attempt_id=None,
            lease_expires_at_utc=None,
        )
    with pytest.raises(ValueError, match="forbids a failure reason"):
        replace(claim, downstream_failure_reason="unexpected_failure")


def test_finalization_rejects_terminal_rewrite_and_non_terminal_posture() -> None:
    accepted = finalize_downstream_submission(
        _claim(),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    ).record
    assert accepted is not None

    repeated = finalize_downstream_submission(
        accepted,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-001",
        posture=DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=2),
        failure_reason="late_rejection",
    )
    with pytest.raises(ValueError, match="unsupported downstream submission final posture"):
        finalize_downstream_submission(
            _claim(),
            lease_owner="downstream-submission",
            lease_attempt_id="attempt-001",
            posture=DownstreamSubmissionPosture.IN_FLIGHT,
            finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        )

    assert repeated.decision is DownstreamSubmissionMutationDecision.INVALID_STATE
    assert repeated.blocker == "downstream_submission_not_in_flight"


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


def _owner_receipt(
    *,
    source_event_version: int = 1,
    source_evidence_fingerprint: str = "sha256:evidence-redacted",
) -> DownstreamSubmissionOwnerReceipt:
    return DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_ADVISE,
        owner_request_id="ipi_001",
        owner_realization_id="ipr_001",
        owner_work_id="iarw_001",
        source_event_version=source_event_version,
        source_evidence_fingerprint=source_evidence_fingerprint,
    )
