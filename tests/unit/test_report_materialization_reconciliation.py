from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast

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
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionMutationResult,
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
_USE_REPOSITORY = object()


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


@pytest.mark.parametrize(
    ("changes", "expected_blocker"),
    (
        (
            {"resource_type": DownstreamSubmissionResourceType.CONVERSION_INTENT},
            "report_materialization_requires_evidence_pack_submission",
        ),
        (
            {"target": ConversionTarget.ADVISE_PROPOSAL},
            "report_materialization_requires_report_target",
        ),
        (
            {"source_authority": SourceSystem.LOTUS_ADVISE},
            "report_materialization_requires_report_authority",
        ),
    ),
)
def test_non_report_submission_identity_is_not_eligible_for_owner_recovery(
    changes: dict[str, object],
    expected_blocker: str,
) -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    submission = repository.downstream_submission_by_support_reference(support_reference)
    assert submission is not None
    submission_repository = SimpleNamespace(
        downstream_submission_by_support_reference=lambda _support_reference: replace(
            submission,
            **changes,
        )
    )
    reader = CapturingReportReader(_authoritative_receipt(evidence_pack))

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=cast(Any, submission_repository),
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.NOT_ELIGIBLE
    assert result.blocker == expected_blocker
    assert reader.call_count == 0


def test_missing_submission_returns_not_found_without_owner_read() -> None:
    reader = CapturingReportReader(cast(DownstreamOwnerReceipt, object()))

    result = reconcile_report_materialization_receipt(
        _command("downstream-submission-0123456789abcdef01234567"),
        repository=InMemoryIdeaRepository(),
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.NOT_FOUND
    assert reader.call_count == 0


def test_missing_local_pack_fails_closed_before_owner_read() -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    reader = CapturingReportReader(_authoritative_receipt(evidence_pack))
    incomplete_repository = _RepositoryOverride(repository, report_evidence_pack=None)

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=cast(Any, incomplete_repository),
        report_reader=reader,
    )

    assert result.status is ReportMaterializationReconciliationStatus.CONFLICT
    assert result.blocker == "report_materialization_source_resource_missing"
    assert reader.call_count == 0


def test_missing_report_reader_retains_uncertain_posture() -> None:
    repository, _evidence_pack, support_reference, _ = _uncertain_submission()

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=repository,
        report_reader=None,
    )

    assert result.status is ReportMaterializationReconciliationStatus.OWNER_UNAVAILABLE
    assert result.blocker == "report_materialization_reader_not_configured"
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED


def test_repository_conflict_cannot_advance_recovered_receipt() -> None:
    repository, evidence_pack, support_reference, _ = _uncertain_submission()
    conflicting_repository = _RepositoryOverride(repository, force_mutation_conflict=True)

    result = reconcile_report_materialization_receipt(
        _command(support_reference),
        repository=cast(Any, conflicting_repository),
        report_reader=CapturingReportReader(_authoritative_receipt(evidence_pack)),
    )

    assert result.status is ReportMaterializationReconciliationStatus.CONFLICT
    assert result.blocker == "concurrent_report_reconciliation"


@pytest.mark.parametrize(
    "changes",
    (
        {"support_reference": " "},
        {"actor_subject": " "},
        {"accepted_at_utc": datetime(2026, 9, 5, 14, 45)},
        {
            "accepted_at_utc": datetime(
                2026,
                9,
                5,
                15,
                45,
                tzinfo=timezone(timedelta(hours=1)),
            )
        },
    ),
)
def test_reconciliation_command_rejects_incomplete_or_untrusted_time(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        replace(_command("downstream-submission-0123456789abcdef01234567"), **changes)


@pytest.mark.parametrize(
    "receipt",
    (
        SimpleNamespace(owner_authority=SourceSystem.LOTUS_ADVISE, report_materialization=None),
        SimpleNamespace(owner_authority=SourceSystem.LOTUS_REPORT, report_materialization=None),
    ),
)
def test_report_receipt_validation_rejects_wrong_authority_or_missing_evidence(
    receipt: object,
) -> None:
    repository = repository_with_report_pack()
    evidence_pack = repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None

    from app.application.downstream_realization.report_receipt_validation import (
        validated_report_submission_receipt,
    )

    with pytest.raises(ValueError):
        validated_report_submission_receipt(cast(DownstreamOwnerReceipt, receipt), evidence_pack)


@dataclass
class _RepositoryOverride:
    repository: InMemoryIdeaRepository
    report_evidence_pack: GovernedReportEvidencePack | None | object = _USE_REPOSITORY
    force_mutation_conflict: bool = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.repository, name)

    def report_evidence_pack_by_id(
        self,
        report_evidence_pack_id: str,
    ) -> GovernedReportEvidencePack | None:
        if self.report_evidence_pack is not _USE_REPOSITORY:
            return cast(GovernedReportEvidencePack | None, self.report_evidence_pack)
        return self.repository.report_evidence_pack_by_id(report_evidence_pack_id)

    def reconcile_downstream_submission(self, **kwargs: Any) -> DownstreamSubmissionMutationResult:
        if self.force_mutation_conflict:
            return DownstreamSubmissionMutationResult(
                decision=DownstreamSubmissionMutationDecision.INVALID_STATE,
                record=self.repository.downstream_submission_by_support_reference(
                    kwargs["support_reference"]
                ),
                blocker="concurrent_report_reconciliation",
            )
        return self.repository.reconcile_downstream_submission(**kwargs)


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
