from __future__ import annotations

from datetime import datetime, timedelta

from app.application.candidate_detail import GetCandidateDetailCommand, get_candidate_detail
from app.application.candidate_lookup import candidate_record_by_id
from app.domain import (
    CandidatePersistenceRecord,
    ConversionTarget,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    IdeaRepositorySnapshot,
    QueueAccessScopeFilter,
    SourceSystem,
    create_downstream_submission_claim,
)
from tests.unit.test_postgres_repository import access_scope, high_cash_candidate


def test_candidate_detail_uses_projection_repository_without_snapshot() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail",
        persisted_at_utc=candidate.created_at_utc,
    )
    repository = ProjectionOnlyCandidateDetailRepository(record)

    result = get_candidate_detail(
        GetCandidateDetailCommand(candidate_id=candidate.candidate_id),
        repository=repository,
    )

    assert result.record == record
    assert result.downstream_submissions == ()
    assert repository.requested_candidate_ids == [candidate.candidate_id]
    assert repository.requested_submission_candidate_ids == [candidate.candidate_id]


def test_candidate_detail_projection_preserves_scope_denial() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail",
        persisted_at_utc=candidate.created_at_utc,
    )
    repository = ProjectionOnlyCandidateDetailRepository(record)

    result = get_candidate_detail(
        GetCandidateDetailCommand(
            candidate_id=candidate.candidate_id,
            access_scope_filter=QueueAccessScopeFilter(portfolio_id="other-portfolio"),
        ),
        repository=repository,
    )

    assert result.record is None
    assert result.access_scope_denied is True
    assert repository.requested_submission_candidate_ids == []


def test_candidate_lookup_falls_back_to_snapshot_for_process_local_repository() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-lookup",
        persisted_at_utc=candidate.created_at_utc,
    )
    repository = SnapshotOnlyCandidateRepository(record)

    assert candidate_record_by_id(repository, candidate.candidate_id) == record
    assert candidate_record_by_id(repository, "missing-candidate") is None
    assert repository.snapshot_reads == 2


def test_candidate_detail_snapshot_fallback_resolves_both_submission_resource_types() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail-snapshot-fallback",
        persisted_at_utc=candidate.created_at_utc,
    )
    conversion = _submission(
        idempotency_key="detail-fallback-conversion",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-fallback-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        submitted_at_utc=candidate.created_at_utc + timedelta(minutes=1),
    )
    report = _submission(
        idempotency_key="detail-fallback-report",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id="report-fallback-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        submitted_at_utc=candidate.created_at_utc,
    )
    repository = SnapshotOnlyCandidateRepository(
        record,
        conversion_intent_candidates={conversion.resource_id: candidate.candidate_id},
        report_evidence_pack_candidates={report.resource_id: candidate.candidate_id},
        downstream_submission_records={
            conversion.idempotency_key: conversion,
            report.idempotency_key: report,
        },
    )

    result = get_candidate_detail(
        GetCandidateDetailCommand(candidate_id=candidate.candidate_id),
        repository=repository,
    )

    assert result.downstream_submissions == (report, conversion)
    assert repository.snapshot_reads == 2


class ProjectionOnlyCandidateDetailRepository:
    def __init__(self, record: CandidatePersistenceRecord) -> None:
        self.record = record
        self.requested_candidate_ids: list[str] = []
        self.requested_submission_candidate_ids: list[str] = []

    def candidate_record_by_id(self, candidate_id: str) -> CandidatePersistenceRecord | None:
        self.requested_candidate_ids.append(candidate_id)
        if candidate_id == self.record.candidate.candidate_id:
            return self.record
        return None

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("candidate detail projection must not hydrate a full snapshot")

    def downstream_submissions_for_candidate(
        self,
        candidate_id: str,
    ) -> tuple[DownstreamSubmissionRecord, ...]:
        self.requested_submission_candidate_ids.append(candidate_id)
        return ()


class SnapshotOnlyCandidateRepository:
    def __init__(
        self,
        record: CandidatePersistenceRecord,
        *,
        conversion_intent_candidates: dict[str, str] | None = None,
        report_evidence_pack_candidates: dict[str, str] | None = None,
        downstream_submission_records: dict[str, DownstreamSubmissionRecord] | None = None,
    ) -> None:
        self.record = record
        self.snapshot_reads = 0
        self.conversion_intent_candidates = conversion_intent_candidates or {}
        self.report_evidence_pack_candidates = report_evidence_pack_candidates or {}
        self.downstream_submission_records = downstream_submission_records or {}

    def snapshot(self) -> IdeaRepositorySnapshot:
        self.snapshot_reads += 1
        return IdeaRepositorySnapshot(
            candidate_records={self.record.candidate.candidate_id: self.record},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates=self.conversion_intent_candidates,
            report_evidence_pack_candidates=self.report_evidence_pack_candidates,
            downstream_submission_records=self.downstream_submission_records,
        )


def _submission(
    *,
    idempotency_key: str,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    target: ConversionTarget,
    source_authority: SourceSystem,
    submitted_at_utc: datetime,
) -> DownstreamSubmissionRecord:
    return create_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint=f"sha256:{idempotency_key}",
        resource_type=resource_type,
        resource_id=resource_id,
        target=target,
        source_authority=source_authority,
        actor_subject="candidate-detail-test",
        claimed_at_utc=submitted_at_utc,
        lease_owner="candidate-detail-test",
        lease_attempt_id=f"attempt-{idempotency_key}",
        lease_expires_at_utc=submitted_at_utc + timedelta(minutes=5),
    )
