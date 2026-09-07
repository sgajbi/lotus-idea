from __future__ import annotations

from app.domain import CandidatePersistenceRecord
from app.ports.idea_repository import (
    CandidateDetailProjectionRepository,
    CandidateSnapshotRepository,
)


def candidate_record_by_id(
    repository: CandidateSnapshotRepository,
    candidate_id: str,
) -> CandidatePersistenceRecord | None:
    if isinstance(repository, CandidateDetailProjectionRepository):
        return repository.candidate_record_by_id(candidate_id)
    snapshot = repository.snapshot()
    return snapshot.candidate_records.get(candidate_id)


def candidate_tenant_id(record: CandidatePersistenceRecord) -> str:
    """Return the trusted durable tenant that scopes candidate-bound mutations."""
    access_scope = record.candidate.access_scope
    if access_scope is None:
        raise ValueError("persisted candidate tenant scope is unavailable")
    return access_scope.tenant_id
