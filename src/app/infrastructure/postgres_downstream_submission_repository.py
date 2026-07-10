from __future__ import annotations

from datetime import datetime

from app.domain.downstream_submission import (
    DownstreamSubmissionClaimResult,
    DownstreamSubmissionMutationResult,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
)
from app.infrastructure.postgres_downstream_submission import (
    claim_postgres_downstream_submission,
    finalize_postgres_downstream_submission,
    load_postgres_downstream_submission_by_idempotency_key,
    load_postgres_downstream_submission_by_support_reference,
    load_postgres_downstream_submissions_requiring_reconciliation,
    reconcile_postgres_downstream_submission,
)
from app.infrastructure.postgres_protocols import PostgresConnection


class PostgresDownstreamSubmissionRepositoryMixin:
    _connection: PostgresConnection

    def downstream_submission_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DownstreamSubmissionRecord | None:
        return load_postgres_downstream_submission_by_idempotency_key(
            self._connection,
            idempotency_key,
        )

    def claim_downstream_submission(
        self,
        record: DownstreamSubmissionRecord,
    ) -> DownstreamSubmissionClaimResult:
        return claim_postgres_downstream_submission(self._connection, record)

    def finalize_downstream_submission(
        self,
        *,
        idempotency_key: str,
        lease_owner: str,
        lease_attempt_id: str,
        posture: DownstreamSubmissionPosture,
        finalized_at_utc: datetime,
        failure_reason: str | None = None,
    ) -> DownstreamSubmissionMutationResult:
        return finalize_postgres_downstream_submission(
            self._connection,
            idempotency_key=idempotency_key,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            posture=posture,
            finalized_at_utc=finalized_at_utc,
            failure_reason=failure_reason,
        )

    def downstream_submissions_requiring_reconciliation(
        self,
        *,
        limit: int = 100,
    ) -> tuple[DownstreamSubmissionRecord, ...]:
        return load_postgres_downstream_submissions_requiring_reconciliation(
            self._connection,
            limit=limit,
        )

    def downstream_submission_by_support_reference(
        self,
        support_reference: str,
    ) -> DownstreamSubmissionRecord | None:
        return load_postgres_downstream_submission_by_support_reference(
            self._connection,
            support_reference,
        )

    def reconcile_downstream_submission(
        self,
        *,
        support_reference: str,
        resolution: DownstreamSubmissionResolution,
        actor_subject: str,
        reason: str,
        change_reference: str,
        reconciled_at_utc: datetime,
    ) -> DownstreamSubmissionMutationResult:
        return reconcile_postgres_downstream_submission(
            self._connection,
            support_reference=support_reference,
            resolution=resolution,
            actor_subject=actor_subject,
            reason=reason,
            change_reference=change_reference,
            reconciled_at_utc=reconciled_at_utc,
        )
