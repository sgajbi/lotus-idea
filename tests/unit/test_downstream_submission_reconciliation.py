from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.downstream_submission_reconciliation import (
    DownstreamSubmissionReconciliationStatus,
    list_downstream_submissions_requiring_reconciliation,
    reconcile_uncertain_downstream_submission,
)
from app.domain import (
    DownstreamSubmissionPosture,
    DownstreamSubmissionResolution,
    InMemoryIdeaRepository,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim


SUBMITTED_AT = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


def test_reconciliation_projection_omits_submission_identity_and_payload() -> None:
    repository = _repository_with_uncertain_submission()

    summaries = list_downstream_submissions_requiring_reconciliation(repository, limit=10)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.support_reference.startswith("downstream-submission-")
    assert summary.submission_posture is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
    assert summary.reconciliation_eligible is True
    assert summary.attempt_count == 1
    assert "secret-idempotency-key" not in str(summary)
    assert "conversion-sensitive" not in str(summary)


def test_reconciliation_is_audited_replay_safe_and_terminal() -> None:
    repository = _repository_with_uncertain_submission()
    support_reference = repository.downstream_submissions_requiring_reconciliation()[
        0
    ].support_reference

    accepted = reconcile_uncertain_downstream_submission(
        repository,
        support_reference=support_reference,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="platform-operator",
        reason="downstream_receipt_verified",
        change_reference="CHG-334-001",
        reconciled_at_utc=SUBMITTED_AT + timedelta(minutes=5),
    )
    replayed = reconcile_uncertain_downstream_submission(
        repository,
        support_reference=support_reference,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject="platform-operator",
        reason="downstream_receipt_verified",
        change_reference="CHG-334-001",
        reconciled_at_utc=SUBMITTED_AT + timedelta(minutes=6),
    )

    assert accepted.status is DownstreamSubmissionReconciliationStatus.ACCEPTED
    assert replayed.status is DownstreamSubmissionReconciliationStatus.REPLAYED
    assert accepted.summary is not None
    assert accepted.summary.submission_posture is DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM
    assert accepted.summary.audit_entry_count == 3
    assert repository.downstream_submissions_requiring_reconciliation() == ()


def _repository_with_uncertain_submission() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    claim = build_downstream_submission_claim(
        idempotency_key="secret-idempotency-key",
        request_fingerprint="sha256:reconciliation-test",
        resource_id="conversion-sensitive",
        submitted_at_utc=SUBMITTED_AT,
    )
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    )
    return repository
