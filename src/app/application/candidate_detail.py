from __future__ import annotations

from dataclasses import dataclass

from app.application.candidate_lookup import candidate_record_by_id
from app.domain import (
    CandidatePersistenceRecord,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    IdeaRepositorySnapshot,
    downstream_submission_sort_key,
)
from app.domain.access_scope import QueueAccessScopeFilter
from app.ports.idea_repository import (
    CandidateDownstreamSubmissionProjectionRepository,
    CandidateSnapshotRepository,
)


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
    downstream_submissions: tuple[DownstreamSubmissionRecord, ...] = ()
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
        downstream_submissions=_downstream_submissions_for_candidate(
            repository,
            command.candidate_id,
        ),
    )


def _downstream_submissions_for_candidate(
    repository: CandidateSnapshotRepository,
    candidate_id: str,
) -> tuple[DownstreamSubmissionRecord, ...]:
    if isinstance(repository, CandidateDownstreamSubmissionProjectionRepository):
        return repository.downstream_submissions_for_candidate(candidate_id)

    snapshot = repository.snapshot()
    return tuple(
        sorted(
            (
                submission
                for submission in snapshot.downstream_submission_records.values()
                if _submission_candidate_id(snapshot, submission) == candidate_id
            ),
            key=downstream_submission_sort_key,
        )
    )


def _submission_candidate_id(
    snapshot: IdeaRepositorySnapshot,
    submission: DownstreamSubmissionRecord,
) -> str | None:
    if submission.resource_type is DownstreamSubmissionResourceType.CONVERSION_INTENT:
        return snapshot.conversion_intent_candidates.get(submission.resource_id)
    return snapshot.report_evidence_pack_candidates.get(submission.resource_id)
