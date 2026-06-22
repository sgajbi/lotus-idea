from __future__ import annotations

from dataclasses import dataclass

from app.domain import CandidatePersistenceRecord
from app.ports.idea_repository import CandidateSnapshotRepository


@dataclass(frozen=True)
class GetCandidateDetailCommand:
    candidate_id: str

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")


@dataclass(frozen=True)
class CandidateDetailResult:
    record: CandidatePersistenceRecord | None


def get_candidate_detail(
    command: GetCandidateDetailCommand,
    *,
    repository: CandidateSnapshotRepository,
) -> CandidateDetailResult:
    snapshot = repository.snapshot()
    return CandidateDetailResult(
        record=snapshot.candidate_records.get(command.candidate_id),
    )
