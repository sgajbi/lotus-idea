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
