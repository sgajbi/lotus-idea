from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    InMemoryIdeaRepository,
    IdeaRepositorySnapshot,
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


def test_in_memory_submission_repository_fails_closed_for_missing_and_blank_lookups() -> None:
    repository = InMemoryIdeaRepository()

    missing_finalize = repository.finalize_downstream_submission(
        idempotency_key="missing-submission",
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-missing",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT,
    )
    missing_reconcile = repository.reconcile_downstream_submission(
        support_reference="downstream-submission-000000000000000000000000",
        resolution=DownstreamSubmissionResolution.QUARANTINED,
        actor_subject="operations-user",
        reason="submission_not_found",
        change_reference="INC-334-MISSING",
        reconciled_at_utc=CLAIMED_AT,
    )

    assert missing_finalize.decision is DownstreamSubmissionMutationDecision.NOT_FOUND
    assert missing_reconcile.decision is DownstreamSubmissionMutationDecision.NOT_FOUND
    with pytest.raises(ValueError, match="limit must be positive"):
        repository.downstream_submissions_requiring_reconciliation(limit=0)
    with pytest.raises(ValueError, match="idempotency_key is required"):
        repository.downstream_submission_by_idempotency_key(" ")
    with pytest.raises(ValueError, match="support_reference is required"):
        repository.downstream_submission_by_support_reference(" ")


def test_in_memory_candidate_projection_covers_both_resource_types_in_stable_order() -> None:
    conversion = _claim("submission-conversion", "fingerprint-conversion")
    report = create_downstream_submission_claim(
        idempotency_key="submission-report",
        request_fingerprint="fingerprint-report",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id="report-pack-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="report-worker-redacted",
        claimed_at_utc=CLAIMED_AT - timedelta(minutes=1),
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-report",
        lease_expires_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )
    unrelated = replace(
        _claim("submission-unrelated", "fingerprint-unrelated"),
        resource_id="conversion-other",
    )
    repository = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={
                "conversion-001": "candidate-owned",
                "conversion-other": "candidate-unrelated",
            },
            report_evidence_pack_candidates={
                "report-pack-001": "candidate-owned",
            },
            downstream_submission_records={
                conversion.idempotency_key: conversion,
                report.idempotency_key: report,
                unrelated.idempotency_key: unrelated,
            },
        )
    )

    submissions = repository.downstream_submissions_for_candidate("candidate-owned")

    assert [(item.resource_type, item.resource_id) for item in submissions] == [
        (DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK, "report-pack-001"),
        (DownstreamSubmissionResourceType.CONVERSION_INTENT, "conversion-001"),
    ]


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
