from __future__ import annotations

from app.application.candidate_detail import GetCandidateDetailCommand, get_candidate_detail
from app.application.candidate_lookup import candidate_record_by_id
from app.domain import CandidatePersistenceRecord, IdeaRepositorySnapshot, QueueAccessScopeFilter
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
    assert repository.requested_candidate_ids == [candidate.candidate_id]


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


class ProjectionOnlyCandidateDetailRepository:
    def __init__(self, record: CandidatePersistenceRecord) -> None:
        self.record = record
        self.requested_candidate_ids: list[str] = []

    def candidate_record_by_id(self, candidate_id: str) -> CandidatePersistenceRecord | None:
        self.requested_candidate_ids.append(candidate_id)
        if candidate_id == self.record.candidate.candidate_id:
            return self.record
        return None

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("candidate detail projection must not hydrate a full snapshot")


class SnapshotOnlyCandidateRepository:
    def __init__(self, record: CandidatePersistenceRecord) -> None:
        self.record = record
        self.snapshot_reads = 0

    def snapshot(self) -> IdeaRepositorySnapshot:
        self.snapshot_reads += 1
        return IdeaRepositorySnapshot(
            candidate_records={self.record.candidate.candidate_id: self.record},
            idempotency_records={},
            idempotency_candidates={},
        )
