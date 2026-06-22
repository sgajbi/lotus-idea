from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain import EvidenceReplayResult, SourceRef
from app.ports.idea_repository import CandidateEvidenceReplayRepository


@dataclass(frozen=True)
class ReplayCandidateEvidenceCommand:
    candidate_id: str
    current_source_refs: tuple[SourceRef, ...]
    evaluated_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        if not self.current_source_refs:
            raise ValueError("current_source_refs is required")
        object.__setattr__(self, "current_source_refs", tuple(self.current_source_refs))


def replay_candidate_evidence(
    command: ReplayCandidateEvidenceCommand,
    *,
    repository: CandidateEvidenceReplayRepository,
) -> EvidenceReplayResult:
    return repository.replay_evidence(
        command.candidate_id,
        current_source_refs=command.current_source_refs,
        evaluated_at_utc=command.evaluated_at_utc,
    )
