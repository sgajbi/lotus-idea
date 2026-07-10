from __future__ import annotations

from datetime import datetime

from app.domain.downstream_submission import (
    DownstreamSubmissionClaimResult,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionMutationResult,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    evaluate_downstream_submission_claim,
    finalize_downstream_submission,
    reconcile_downstream_submission,
)


class InMemoryDownstreamSubmissionRepositoryMixin:
    _downstream_submission_records: dict[str, DownstreamSubmissionRecord]

    def downstream_submission_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DownstreamSubmissionRecord | None:
        _require_text(idempotency_key, "idempotency_key")
        return self._downstream_submission_records.get(idempotency_key)

    def claim_downstream_submission(
        self,
        record: DownstreamSubmissionRecord,
    ) -> DownstreamSubmissionClaimResult:
        existing = self._downstream_submission_records.get(record.idempotency_key)
        decision = evaluate_downstream_submission_claim(
            existing,
            request_fingerprint=record.request_fingerprint,
        )
        if existing is None:
            self._downstream_submission_records[record.idempotency_key] = record
            existing = record
        return DownstreamSubmissionClaimResult(decision=decision, record=existing)

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
        existing = self._downstream_submission_records.get(idempotency_key)
        if existing is None:
            return DownstreamSubmissionMutationResult(
                decision=DownstreamSubmissionMutationDecision.NOT_FOUND,
                record=None,
                blocker="downstream_submission_not_found",
            )
        result = finalize_downstream_submission(
            existing,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            posture=posture,
            finalized_at_utc=finalized_at_utc,
            failure_reason=failure_reason,
        )
        if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
            assert result.record is not None
            self._downstream_submission_records[idempotency_key] = result.record
        return result

    def downstream_submissions_requiring_reconciliation(
        self,
        *,
        limit: int = 100,
    ) -> tuple[DownstreamSubmissionRecord, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        records = sorted(
            (
                record
                for record in self._downstream_submission_records.values()
                if record.status
                in {
                    DownstreamSubmissionPosture.IN_FLIGHT,
                    DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
                }
            ),
            key=lambda record: (record.updated_at_utc, record.support_reference),
        )
        return tuple(records[:limit])

    def downstream_submission_by_support_reference(
        self,
        support_reference: str,
    ) -> DownstreamSubmissionRecord | None:
        _require_text(support_reference, "support_reference")
        return next(
            (
                record
                for record in self._downstream_submission_records.values()
                if record.support_reference == support_reference
            ),
            None,
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
        existing = self.downstream_submission_by_support_reference(support_reference)
        if existing is None:
            return DownstreamSubmissionMutationResult(
                decision=DownstreamSubmissionMutationDecision.NOT_FOUND,
                record=None,
                blocker="downstream_submission_not_found",
            )
        result = reconcile_downstream_submission(
            existing,
            resolution=resolution,
            actor_subject=actor_subject,
            reason=reason,
            change_reference=change_reference,
            reconciled_at_utc=reconciled_at_utc,
        )
        if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
            assert result.record is not None
            self._downstream_submission_records[existing.idempotency_key] = result.record
        return result


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
