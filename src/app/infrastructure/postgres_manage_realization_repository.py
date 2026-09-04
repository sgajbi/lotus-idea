from __future__ import annotations

from datetime import UTC, datetime

from app.domain import (
    ManageActionRealizationHistory,
    ManageRealizationHistoryMutationResult,
)
from app.infrastructure.postgres_manage_realization import (
    load_postgres_manage_realization_history,
    persist_postgres_manage_realization_history,
)
from app.infrastructure.postgres_protocols import PostgresConnection


class PostgresManageRealizationRepositoryMixin:
    _connection: PostgresConnection

    def manage_realization_history_by_support_reference(
        self,
        support_reference: str,
    ) -> ManageActionRealizationHistory | None:
        return load_postgres_manage_realization_history(
            self._connection,
            support_reference,
        )

    def persist_manage_realization_history(
        self,
        *,
        support_reference: str,
        history: ManageActionRealizationHistory,
    ) -> ManageRealizationHistoryMutationResult:
        return persist_postgres_manage_realization_history(
            self._connection,
            support_reference=support_reference,
            history=history,
            persisted_at_utc=datetime.now(UTC),
        )
