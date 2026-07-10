from __future__ import annotations

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
    SourceSystem,
    create_downstream_submission_claim,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection


CLAIMED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_postgres_claim_survives_restart_and_distinguishes_conflict() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)

    accepted = repository.claim_downstream_submission(_claim("fingerprint-a"))
    restarted = PostgresIdeaRepository(connection)
    repeated = restarted.claim_downstream_submission(_claim("fingerprint-a"))
    conflict = restarted.claim_downstream_submission(_claim("fingerprint-b"))

    assert accepted.decision is DownstreamSubmissionClaimDecision.ACCEPTED
    assert repeated.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
    assert conflict.decision is DownstreamSubmissionClaimDecision.CONFLICT
    assert len(connection.rows["idea_downstream_submission"]) == 1


def test_postgres_finalization_failure_preserves_durable_in_flight_claim() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    connection.fail_on_update = "idea_downstream_submission"

    with pytest.raises(RuntimeError, match="update failed"):
        repository.finalize_downstream_submission(
            idempotency_key="submission-key",
            lease_owner="downstream-submission",
            lease_attempt_id="attempt-submission-key",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        )

    connection.fail_on_update = None
    restarted = PostgresIdeaRepository(connection)
    persisted = restarted.downstream_submission_by_idempotency_key("submission-key")
    retry = restarted.claim_downstream_submission(_claim("fingerprint-a"))

    assert persisted is not None
    assert persisted.status is DownstreamSubmissionPosture.IN_FLIGHT
    assert retry.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
    assert connection.rollbacks == 1


def test_postgres_reconciliation_uses_opaque_reference_and_is_audited() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    finalized = repository.finalize_downstream_submission(
        idempotency_key="submission-key",
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-key",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    )
    assert finalized.decision is DownstreamSubmissionMutationDecision.ACCEPTED

    restarted = PostgresIdeaRepository(connection)
    pending = restarted.downstream_submissions_requiring_reconciliation(limit=10)
    result = restarted.reconcile_downstream_submission(
        support_reference=pending[0].support_reference,
        resolution=DownstreamSubmissionResolution.QUARANTINED,
        actor_subject="operations-user",
        reason="downstream_receipt_unverifiable",
        change_reference="INC-334-001",
        reconciled_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )

    assert len(pending) == 1
    assert "submission-key" not in pending[0].support_reference
    assert result.decision is DownstreamSubmissionMutationDecision.ACCEPTED
    assert result.record is not None
    assert result.record.status is DownstreamSubmissionPosture.QUARANTINED
    assert result.record.audit_history[-1].change_reference == "INC-334-001"
    assert restarted.downstream_submissions_requiring_reconciliation(limit=10) == ()


def _claim(request_fingerprint: str) -> DownstreamSubmissionRecord:
    return create_downstream_submission_claim(
        idempotency_key="submission-key",
        request_fingerprint=request_fingerprint,
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject="advisor-redacted",
        claimed_at_utc=CLAIMED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-key",
        lease_expires_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )
