from __future__ import annotations

from datetime import datetime

from app.domain.downstream_submission import (
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionClaimResult,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionMutationResult,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    downstream_submission_identity,
    downstream_submission_sort_key,
    evaluate_downstream_submission_claim,
    finalize_downstream_submission,
    reconcile_downstream_submission,
)


class InMemoryDownstreamSubmissionRepositoryMixin:
    _downstream_submission_records: dict[str, DownstreamSubmissionRecord]
    _conversion_intent_candidates: dict[str, str]
    _report_evidence_pack_candidates: dict[str, str]

    def downstream_submissions_for_candidate(
        self,
        candidate_id: str,
    ) -> tuple[DownstreamSubmissionRecord, ...]:
        _require_text(candidate_id, "candidate_id")
        records = (
            record
            for record in self._downstream_submission_records.values()
            if self._candidate_id_for_submission(record) == candidate_id
        )
        return tuple(
            sorted(
                records,
                key=downstream_submission_sort_key,
            )
        )

    def _candidate_id_for_submission(self, record: DownstreamSubmissionRecord) -> str | None:
        if record.resource_type is DownstreamSubmissionResourceType.CONVERSION_INTENT:
            return self._conversion_intent_candidates.get(record.resource_id)
        return self._report_evidence_pack_candidates.get(record.resource_id)

    def downstream_submission_by_idempotency_key(
        self,
        tenant_id: str,
        idempotency_key: str,
    ) -> DownstreamSubmissionRecord | None:
        _require_text(tenant_id, "tenant_id")
        _require_text(idempotency_key, "idempotency_key")
        return self._downstream_submission_records.get(
            downstream_submission_identity(tenant_id, idempotency_key)
        )

    def claim_downstream_submission(
        self,
        record: DownstreamSubmissionRecord,
    ) -> DownstreamSubmissionClaimResult:
        storage_key = downstream_submission_identity(record.tenant_id, record.idempotency_key)
        existing = self._downstream_submission_records.get(storage_key)
        resource_existing = next(
            (
                retained
                for retained in self._downstream_submission_records.values()
                if retained.tenant_id == record.tenant_id
                and retained.resource_type is record.resource_type
                and retained.resource_id == record.resource_id
                and retained.target is record.target
            ),
            None,
        )
        if existing is None and resource_existing is not None:
            return DownstreamSubmissionClaimResult(
                decision=DownstreamSubmissionClaimDecision.RESOURCE_CONFLICT,
                record=resource_existing,
            )
        decision = evaluate_downstream_submission_claim(
            existing,
            request_fingerprint=record.request_fingerprint,
        )
        if existing is None:
            self._downstream_submission_records[storage_key] = record
            existing = record
        return DownstreamSubmissionClaimResult(decision=decision, record=existing)

    def finalize_downstream_submission(
        self,
        *,
        tenant_id: str,
        idempotency_key: str,
        lease_owner: str,
        lease_attempt_id: str,
        posture: DownstreamSubmissionPosture,
        finalized_at_utc: datetime,
        failure_reason: str | None = None,
        owner_receipt: DownstreamSubmissionOwnerReceipt | None = None,
    ) -> DownstreamSubmissionMutationResult:
        storage_key = downstream_submission_identity(tenant_id, idempotency_key)
        existing = self._downstream_submission_records.get(storage_key)
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
            owner_receipt=owner_receipt,
        )
        if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
            assert result.record is not None
            self._downstream_submission_records[storage_key] = result.record
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
        owner_receipt: DownstreamSubmissionOwnerReceipt | None = None,
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
            owner_receipt=owner_receipt,
        )
        if result.decision is DownstreamSubmissionMutationDecision.ACCEPTED:
            assert result.record is not None
            storage_key = downstream_submission_identity(
                existing.tenant_id,
                existing.idempotency_key,
            )
            self._downstream_submission_records[storage_key] = result.record
        return result


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
