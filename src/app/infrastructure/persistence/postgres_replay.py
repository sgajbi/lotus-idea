from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.domain.ideas import SourceRef
from app.domain.persistence import (
    EvidencePackPersistenceResult,
    EvidenceReplayResult,
    InMemoryIdeaRepository,
)
from app.infrastructure.persistence.aggregate_mutation import (
    load_candidate_replay_snapshot,
    load_idempotency_replay_snapshot,
)
from app.infrastructure.postgres_protocols import PostgresConnection


class PostgresEvidenceReplayRepositoryMixin:
    _connection: PostgresConnection

    def replay_evidence(
        self,
        candidate_id: str,
        *,
        current_source_refs: tuple[SourceRef, ...],
        evaluated_at_utc: datetime | None = None,
    ) -> EvidenceReplayResult:
        repository = InMemoryIdeaRepository(
            load_candidate_replay_snapshot(self._connection, candidate_id)
        )
        return repository.replay_evidence(
            candidate_id,
            current_source_refs=current_source_refs,
            evaluated_at_utc=evaluated_at_utc,
        )

    def precheck_evidence_pack_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> EvidencePackPersistenceResult | None:
        repository = InMemoryIdeaRepository(
            load_idempotency_replay_snapshot(self._connection, idempotency_key)
        )
        return repository.precheck_evidence_pack_mutation(
            idempotency_key=idempotency_key,
            payload=payload,
        )
