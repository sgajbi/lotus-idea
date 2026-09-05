from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest

from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeReportEvidencePackCommand,
    submit_report_evidence_pack_to_downstream,
)
from app.application.report_materialization_reconciliation import (
    ReconcileReportMaterializationCommand,
    ReportMaterializationAccessScopeDenied,
    ReportMaterializationReconciliationStatus,
    reconcile_report_materialization_receipt,
)
from app.domain import (
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    ConversionTarget,
    GovernedReportEvidencePack,
    InMemoryIdeaRepository,
    QueueAccessScopeFilter,
    ReportMaterializationReceiptEvidence,
    ReviewAccessScope,
    SourceSystem,
    create_downstream_submission_claim,
)
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationReadConflict,
    DownstreamRealizationOutcome,
    DownstreamRealizationReadError,
)
from tests.support.report_materialization import authoritative_report_outcome
from tests.unit.test_downstream_realization_application import (
    AUTHORIZED_SCOPE_FILTER,
    repository_with_report_pack,
)


ACCEPTED_AT = datetime(2026, 9, 5, 14, 45, tzinfo=UTC)


@dataclass
class RaisingReportSubmitClient:
    call_count: int = 0

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.call_count += 1
        raise RuntimeError("Report committed but its response was lost")


@dataclass
class CapturingReportReader:
    receipt: DownstreamOwnerReceipt
    call_count: int = 0
    access_scope: ReviewAccessScope | None = None
    idempotency_key: str | None = None

    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        self.call_count += 1
        self.access_scope = access_scope
        self.idempotency_key = idempotency_key
        return self.receipt


class UnavailableReportReader(CapturingReportReader):
    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        self.call_count += 1
        raise DownstreamRealizationReadError("owner unavailable")


class ConflictingReportReader(CapturingReportReader):
    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        self.call_count += 1
        raise DownstreamRealizationReadConflict("owner identity conflict")


def test_recovers_uncertain_report_receipt_and_exactly_replays_without_another_owner_read() -> None:
    repository, evidence_pack, support_reference, submit_client = _uncertain_submission()
    receipt = _authoritative_receipt(evidence_pack)
    reader = CapturingReportReader(receipt)
    command = _command(support_reference)

    accepted = reconcile_report_materialization_receipt(
        command,
        repository=repository,
        report_reader=reader,
    )
    replayed = reconcile_report_materialization_receipt(
        command,
        repository=repository,
        report_reader=reader,
    )

    assert accepted.status is ReportMaterializationReconciliationStatus.ACCEPTED
    assert accepted.owner_receipt is not None
    assert accepted.owner_receipt.owner_realization_id == receipt.owner_realization_id
    assert replayed.status is ReportMaterializationReconciliationStatus.REPLAYED
    assert replayed.owner_receipt == accepted.owner_receipt
    assert reader.call_count == 1
    assert reader.idempotency_key == "submission-report-recovery-001"
    assert reader.access_scope == evidence_pack_scope()
    assert submit_client.call_count == 1
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM
    assert persisted.owner_receipt == accepted.owner_receipt
    assert len(persisted.audit_history) == 3
    assert persisted.updated_at_utc == ACCEPTED_AT
    assert persisted.audit_history[-1].occurred_at_utc == ACCEPTED_AT


@pytest.mark.parametrize(
    "field_name",
    (
        "report_evidence_pack_id",
        "conversion_intent_id",
        "candidate_id",
        "evidence_packet_id",
        "source_evidence_fingerprint",
    ),
)
def test_rejects_every_recovered_report_identity_mismatch_without_advancing(
    field_name: str,
) -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    receipt = _authoritative_receipt(evidence_pack)
    if field_name == "source_evidence_fingerprint":
        receipt = replace(receipt, source_evidence_fingerprint="sha256:contradictory-evidence")
    else:
        assert receipt.report_materialization is not None
        contradictory_evidence = _with_contradictory_identity(
            receipt.report_materialization,
            field_name,
        )
        receipt = replace(
            receipt,
            report_materialization=contradictory_evidence,
        )

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=repository,
        report_reader=CapturingReportReader(receipt),
    )

    assert result.status is ReportMaterializationReconciliationStatus.CONFLICT
    assert result.blocker == "report_materialization_receipt_invalid"
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
    assert persisted.owner_receipt is None
    assert len(persisted.audit_history) == 2


def test_owner_unavailability_retains_uncertain_posture_and_receipt_absence() -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    reader = UnavailableReportReader(_authoritative_receipt(evidence_pack))

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=repository,
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.OWNER_UNAVAILABLE
    assert result.blocker == "report_materialization_owner_unavailable"
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
    assert persisted.owner_receipt is None
    assert len(persisted.audit_history) == 2


def test_owner_identity_conflict_is_reported_without_advancing_uncertain_posture() -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    reader = ConflictingReportReader(_authoritative_receipt(evidence_pack))

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=repository,
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.CONFLICT
    assert result.blocker == "report_materialization_owner_identity_conflict"
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
    assert persisted.owner_receipt is None
    assert len(persisted.audit_history) == 2


def test_scope_denial_occurs_before_report_owner_read() -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    reader = CapturingReportReader(_authoritative_receipt(evidence_pack))

    with pytest.raises(ReportMaterializationAccessScopeDenied):
        reconcile_report_materialization_receipt(
            replace(
                _command(support_reference),
                access_scope_filter=QueueAccessScopeFilter(
                    tenant_id="tenant-other",
                    book_id="book-private-bank-sg",
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                    client_id="client-redacted",
                ),
            ),
            repository=repository,
            report_reader=reader,
        )

    assert reader.call_count == 0
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED


def test_active_in_flight_submission_cannot_be_reconciled_while_post_may_still_run() -> None:
    repository = repository_with_report_pack()
    evidence_pack = repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    claim = create_downstream_submission_claim(
        idempotency_key="active-report-submission",
        request_fingerprint="sha256:active-report-submission",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id=evidence_pack.report_evidence_pack_id,
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="advisor-redacted",
        claimed_at_utc=ACCEPTED_AT,
        lease_owner="report-worker",
        lease_attempt_id="report-attempt-001",
        lease_expires_at_utc=ACCEPTED_AT + timedelta(minutes=1),
    )
    repository.claim_downstream_submission(claim)
    reader = CapturingReportReader(_authoritative_receipt(evidence_pack))

    result = reconcile_report_materialization_receipt(
        _command(claim.support_reference),
        repository=repository,
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.NOT_ELIGIBLE
    assert result.blocker == "report_materialization_submission_not_recoverable"
    assert reader.call_count == 0


def _uncertain_submission() -> tuple[
    InMemoryIdeaRepository,
    GovernedReportEvidencePack,
    str,
    RaisingReportSubmitClient,
]:
    repository = repository_with_report_pack()
    evidence_pack = repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    submit_client = RaisingReportSubmitClient()
    result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(
            report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
            idempotency_key="submission-report-recovery-001",
            actor_subject="advisor-redacted",
            access_scope_filter=AUTHORIZED_SCOPE_FILTER,
            submitted_at_utc=ACCEPTED_AT,
        ),
        repository=repository,
        report_client=submit_client,
    )
    assert result.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    pending = repository.downstream_submissions_requiring_reconciliation(limit=10)
    assert len(pending) == 1
    return repository, evidence_pack, pending[0].support_reference, submit_client


def _with_contradictory_identity(
    evidence: ReportMaterializationReceiptEvidence,
    field_name: str,
) -> ReportMaterializationReceiptEvidence:
    value = f"contradictory-{field_name}"
    if field_name == "report_evidence_pack_id":
        return replace(evidence, report_evidence_pack_id=value)
    if field_name == "conversion_intent_id":
        return replace(evidence, conversion_intent_id=value)
    if field_name == "candidate_id":
        return replace(evidence, candidate_id=value)
    if field_name == "evidence_packet_id":
        return replace(evidence, evidence_packet_id=value)
    raise AssertionError(f"unsupported identity field: {field_name}")


def _authoritative_receipt(evidence_pack: GovernedReportEvidencePack) -> DownstreamOwnerReceipt:
    receipt = authoritative_report_outcome(evidence_pack).owner_receipt
    assert receipt is not None
    return receipt


def _command(support_reference: str) -> ReconcileReportMaterializationCommand:
    return ReconcileReportMaterializationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        accepted_at_utc=ACCEPTED_AT,
        correlation_id="corr-report-recovery",
        trace_id="trace-report-recovery",
    )


def evidence_pack_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-sg",
        book_id="book-private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-redacted",
    )
