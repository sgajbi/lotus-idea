from __future__ import annotations

from dataclasses import dataclass

from app.application.candidate_lookup import candidate_record_by_id
from app.domain import CandidatePersistenceRecord
from app.domain.access_scope import QueueAccessScopeFilter
from app.ports.idea_repository import CandidateSnapshotRepository


@dataclass(frozen=True)
class GetCandidateDetailCommand:
    candidate_id: str
    access_scope_filter: QueueAccessScopeFilter | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")


@dataclass(frozen=True)
class CandidateDetailResult:
    record: CandidatePersistenceRecord | None
    access_scope_denied: bool = False


def get_candidate_detail(
    command: GetCandidateDetailCommand,
    *,
    repository: CandidateSnapshotRepository,
) -> CandidateDetailResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return CandidateDetailResult(record=None)
    if command.access_scope_filter is not None and not command.access_scope_filter.matches(
        record.candidate.access_scope
    ):
        return CandidateDetailResult(record=None, access_scope_denied=True)
    return CandidateDetailResult(
        record=record,
    )
