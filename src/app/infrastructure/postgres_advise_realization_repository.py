from __future__ import annotations

from datetime import UTC, datetime

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationResult,
)
from app.infrastructure.postgres_advise_realization import (
    load_postgres_advise_realization_history,
    persist_postgres_advise_realization_history,
)
from app.infrastructure.postgres_protocols import PostgresConnection


class PostgresAdviseRealizationRepositoryMixin:
    _connection: PostgresConnection

    def advise_realization_history_by_support_reference(
        self,
        support_reference: str,
    ) -> AdviseProposalRealizationHistory | None:
        return load_postgres_advise_realization_history(
            self._connection,
            support_reference,
        )

    def persist_advise_realization_history(
        self,
        *,
        support_reference: str,
        history: AdviseProposalRealizationHistory,
    ) -> AdviseRealizationHistoryMutationResult:
        return persist_postgres_advise_realization_history(
            self._connection,
            support_reference=support_reference,
            history=history,
            persisted_at_utc=datetime.now(UTC),
        )
