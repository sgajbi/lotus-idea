from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    InMemoryIdeaRepository,
    SourceSystem,
    create_downstream_submission_claim,
)


CLAIMED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_in_memory_claim_is_atomic_replay_safe_and_conflict_aware() -> None:
    repository = InMemoryIdeaRepository()
    record = _claim("submission-key", "fingerprint-a")

    accepted = repository.claim_downstream_submission(record)
    repeated = repository.claim_downstream_submission(record)
    conflict = repository.claim_downstream_submission(_claim("submission-key", "fingerprint-b"))

    assert accepted.decision is DownstreamSubmissionClaimDecision.ACCEPTED
    assert repeated.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
    assert conflict.decision is DownstreamSubmissionClaimDecision.CONFLICT
    assert repository.downstream_submission_by_idempotency_key("submission-key") == record


def test_in_memory_finalize_is_lease_fenced_and_terminal_replays() -> None:
    repository = InMemoryIdeaRepository()
    repository.claim_downstream_submission(_claim("submission-key", "fingerprint-a"))

    conflict = repository.finalize_downstream_submission(
        idempotency_key="submission-key",
        lease_owner="other-worker",
        lease_attempt_id="other-attempt",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    )
    finalized = repository.finalize_downstream_submission(
        idempotency_key="submission-key",
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-key",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    )
    replay = repository.claim_downstream_submission(_claim("submission-key", "fingerprint-a"))

    assert conflict.decision is DownstreamSubmissionMutationDecision.LEASE_CONFLICT
    assert finalized.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert replay.decision is DownstreamSubmissionClaimDecision.REPLAYED


def test_in_memory_reconciliation_is_source_safe_and_audited() -> None:
    repository = InMemoryIdeaRepository()
    repository.claim_downstream_submission(_claim("submission-key", "fingerprint-a"))
    repository.finalize_downstream_submission(
        idempotency_key="submission-key",
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-key",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    )
    pending = repository.downstream_submissions_requiring_reconciliation(limit=10)

    reconciled = repository.reconcile_downstream_submission(
        support_reference=pending[0].support_reference,
        resolution=DownstreamSubmissionResolution.QUARANTINED,
        actor_subject="operations-user",
        reason="downstream_receipt_unverifiable",
        change_reference="INC-334-001",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )

    assert len(pending) == 1
    assert "submission-key" not in pending[0].support_reference
    assert reconciled.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert reconciled.record is not None
    assert reconciled.record.status is DownstreamSubmissionPosture.QUARANTINED
    assert repository.downstream_submissions_requiring_reconciliation(limit=10) == ()


def _claim(idempotency_key: str, request_fingerprint: str) -> DownstreamSubmissionRecord:
    return create_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject="advisor-redacted",
        claimed_at_utc=CLAIMED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id=f"attempt-{idempotency_key}",
        lease_expires_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )
