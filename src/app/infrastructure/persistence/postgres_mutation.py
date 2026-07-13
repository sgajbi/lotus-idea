from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.domain.conversion_outcome_policy import ConversionOutcomeIdentity
from app.domain.persistence import IdeaRepositorySnapshot, InMemoryIdeaRepository
from app.domain.review_governance import ReviewMutationIdentity
from app.infrastructure.persistence.aggregate_mutation import (
    RelatedCandidateIdsLoader,
    load_candidate_mutation_snapshot,
    load_idempotency_mutation_snapshot,
)
from app.infrastructure.postgres_conversion_outcome import (
    load_postgres_conversion_outcome_identity,
)
from app.infrastructure.postgres_downstream_lookup import (
    load_candidate_id_for_conversion_intent_mutation,
)
from app.infrastructure.postgres_mutation_retry import execute_postgres_mutation
from app.infrastructure.postgres_protocols import PostgresConnection
from app.infrastructure.postgres_review_identity import load_postgres_review_identity


_ResultT = TypeVar("_ResultT")


class PostgresBoundedMutationRepositoryMixin:
    _connection: PostgresConnection

    def _mutate_candidate(
        self,
        *,
        candidate_ids: tuple[str, ...],
        operation: Callable[[InMemoryIdeaRepository], _ResultT],
        idempotency_key: str | None = None,
        identity_keys: tuple[str, ...] = (),
        related_candidate_ids_loader: RelatedCandidateIdsLoader | None = None,
    ) -> _ResultT:
        def snapshot_loader() -> IdeaRepositorySnapshot:
            return load_candidate_mutation_snapshot(
                self._connection,
                candidate_ids=candidate_ids,
                idempotency_key=idempotency_key,
                identity_keys=identity_keys,
                related_candidate_ids_loader=related_candidate_ids_loader,
            )

        return execute_postgres_mutation(
            self,
            self._connection,
            snapshot_loader,
            snapshot_loader,
            operation,
        )

    def _mutate_idempotency(
        self,
        idempotency_key: str,
        *,
        operation: Callable[[InMemoryIdeaRepository], _ResultT],
    ) -> _ResultT:
        def snapshot_loader() -> IdeaRepositorySnapshot:
            return load_idempotency_mutation_snapshot(self._connection, idempotency_key)

        return execute_postgres_mutation(
            self,
            self._connection,
            snapshot_loader,
            snapshot_loader,
            operation,
        )

    def _review_identity_candidate_ids(
        self,
        identity: ReviewMutationIdentity,
    ) -> tuple[str, ...]:
        existing = load_postgres_review_identity(self._connection, identity)
        return (existing.candidate_id,) if existing is not None else ()

    def _conversion_intent_candidate_ids(
        self,
        conversion_intent_id: str,
    ) -> tuple[str, ...]:
        candidate_id = load_candidate_id_for_conversion_intent_mutation(
            self._connection,
            conversion_intent_id,
        )
        return (candidate_id,) if candidate_id is not None else ()

    def _conversion_outcome_candidate_ids(
        self,
        identity: ConversionOutcomeIdentity,
    ) -> tuple[str, ...]:
        candidate_ids = set(self._conversion_intent_candidate_ids(identity.conversion_intent_id))
        existing = load_postgres_conversion_outcome_identity(
            self._connection,
            identity.conversion_outcome_id,
        )
        if existing is not None:
            candidate_ids.update(
                self._conversion_intent_candidate_ids(existing.conversion_intent_id)
            )
        return tuple(sorted(candidate_ids))
