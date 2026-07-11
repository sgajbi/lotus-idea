from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

import app.infrastructure.postgres_downstream_submission as postgres_submission
from app.domain import (
    ConversionTarget,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    IdeaRepositorySnapshot,
    SourceSystem,
    create_downstream_submission_claim,
    downstream_submission_support_reference,
)
from app.infrastructure.postgres_repository_delta import _mutated_candidate_ids
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_data_lifecycle import DataLifecycleWriteBlockedError
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


def test_postgres_claim_rejects_erased_resource_before_delivery_insert() -> None:
    connection = FakePostgresConnection()
    connection.rows["idea_conversion_intent"].append(
        {"conversion_intent_id": "conversion-001", "candidate_id": "candidate-erased"}
    )
    connection.rows["idea_data_lifecycle_control"].append(
        {
            "candidate_id": "candidate-erased",
            "state": "erased",
            "held_from_state": None,
        }
    )

    with pytest.raises(DataLifecycleWriteBlockedError) as error:
        PostgresIdeaRepository(connection).claim_downstream_submission(_claim("fingerprint-a"))

    assert error.value.blocker == "candidate_erased"
    assert connection.rows["idea_downstream_submission"] == []
    assert connection.rollbacks == 1


def test_new_downstream_submissions_resolve_candidates_for_lifecycle_fencing() -> None:
    conversion_claim = _claim("fingerprint-conversion")
    report_claim = replace(
        _claim("fingerprint-report"),
        idempotency_key="report-submission-key",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id="report-pack-001",
        support_reference=downstream_submission_support_reference("report-submission-key"),
    )
    before = IdeaRepositorySnapshot({}, {}, {})
    after = IdeaRepositorySnapshot(
        {},
        {},
        {},
        conversion_intent_candidates={"conversion-001": "candidate-conversion"},
        report_evidence_pack_candidates={"report-pack-001": "candidate-report"},
        downstream_submission_records={
            conversion_claim.idempotency_key: conversion_claim,
            report_claim.idempotency_key: report_claim,
        },
    )

    assert _mutated_candidate_ids(before, after) == {
        "candidate-conversion",
        "candidate-report",
    }
    assert _mutated_candidate_ids(after, after) == set()


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


def test_postgres_submission_mutations_fail_closed_for_missing_or_competing_claims() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)

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
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    lease_conflict = repository.finalize_downstream_submission(
        idempotency_key="submission-key",
        lease_owner="competing-worker",
        lease_attempt_id="attempt-competing",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
    )

    assert missing_finalize.decision is DownstreamSubmissionMutationDecision.NOT_FOUND
    assert missing_reconcile.decision is DownstreamSubmissionMutationDecision.NOT_FOUND
    assert lease_conflict.decision is DownstreamSubmissionMutationDecision.LEASE_CONFLICT
    assert (
        repository.downstream_submission_by_support_reference(
            lease_conflict.record.support_reference if lease_conflict.record else ""
        )
        == lease_conflict.record
    )
    with pytest.raises(ValueError, match="limit must be positive"):
        repository.downstream_submissions_requiring_reconciliation(limit=0)


@pytest.mark.parametrize(
    ("audit_json", "message"),
    [
        ("not-an-array", "audit_json must be an array"),
        (["not-an-object"], "audit_json entries must be objects"),
    ],
)
def test_postgres_submission_decoder_rejects_malformed_audit_history(
    audit_json: object,
    message: str,
) -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    connection.rows["idea_downstream_submission"][0]["audit_json"] = audit_json

    with pytest.raises(ValueError, match=message):
        repository.downstream_submission_by_idempotency_key("submission-key")


def test_postgres_submission_decoder_rejects_blank_persisted_identifiers() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    connection.rows["idea_downstream_submission"][0]["resource_id"] = ""

    with pytest.raises(ValueError, match="resource_id is required"):
        repository.downstream_submission_by_idempotency_key("submission-key")


def test_postgres_submission_decoder_rejects_blank_optional_audit_values() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    repository.claim_downstream_submission(_claim("fingerprint-a"))
    audit_json = connection.rows["idea_downstream_submission"][0]["audit_json"]
    assert isinstance(audit_json, list)
    audit_json[0]["reason"] = ""

    with pytest.raises(ValueError, match="reason must be a non-blank string"):
        repository.downstream_submission_by_idempotency_key("submission-key")


def test_postgres_submission_claim_fails_closed_for_unresolved_unique_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = _claim("fingerprint-a")
    repository.claim_downstream_submission(claim)
    monkeypatch.setattr(
        postgres_submission, "_load_by_idempotency_key", lambda *args, **kwargs: None
    )

    monkeypatch.setattr(
        postgres_submission,
        "_load_by_support_reference",
        lambda *args, **kwargs: claim,
    )
    with pytest.raises(RuntimeError, match="support reference collision"):
        postgres_submission.claim_postgres_downstream_submission(connection, claim)

    monkeypatch.setattr(
        postgres_submission,
        "_load_by_support_reference",
        lambda *args, **kwargs: None,
    )
    with pytest.raises(RuntimeError, match="claim conflict was not recoverable"):
        postgres_submission.claim_postgres_downstream_submission(connection, claim)

    assert connection.rollbacks == 2


def test_postgres_submission_reconciliation_rolls_back_failed_state_commit() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = _claim("fingerprint-a")
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=CLAIMED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    )
    connection.fail_on_update = "idea_downstream_submission"

    with pytest.raises(RuntimeError, match="update failed"):
        repository.reconcile_downstream_submission(
            support_reference=claim.support_reference,
            resolution=DownstreamSubmissionResolution.QUARANTINED,
            actor_subject="operations-user",
            reason="receipt_unverifiable",
            change_reference="INC-334-ROLLBACK",
            reconciled_at_utc=CLAIMED_AT + timedelta(minutes=2),
        )

    assert connection.rollbacks == 1


def test_postgres_submission_state_update_is_lease_fenced() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = _claim("fingerprint-a")
    repository.claim_downstream_submission(claim)

    with connection.cursor() as cursor, pytest.raises(RuntimeError, match="lost its lease"):
        postgres_submission._update_mutable_submission_state(
            cursor,
            replace(claim, lease_attempt_id="attempt-stale"),
        )


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
