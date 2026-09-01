from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    SourceSystem,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_advise_realization_reconciliation import RECORDED_AT, _history
from tests.unit.test_postgres_downstream_submission import _claim


def test_postgres_advise_history_survives_restart_and_appends_monotonically() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = _claim("fingerprint-a")
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=RECORDED_AT + timedelta(minutes=1),
        owner_receipt=DownstreamSubmissionOwnerReceipt(
            owner_authority=SourceSystem.LOTUS_ADVISE,
            owner_request_id="ipi_001",
            owner_realization_id="ipr_001",
            owner_work_id="iarw_001",
            source_event_version=1,
            source_evidence_fingerprint="sha256:downstream-evidence",
        ),
    )

    accepted = repository.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=_postgres_history(version=2),
    )
    restarted = PostgresIdeaRepository(connection)
    replayed = restarted.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=_postgres_history(version=2),
    )
    progressed = restarted.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=_postgres_history(version=3),
    )

    assert accepted.decision is AdviseRealizationHistoryMutationDecision.ACCEPTED
    assert replayed.decision is AdviseRealizationHistoryMutationDecision.REPLAYED
    assert progressed.decision is AdviseRealizationHistoryMutationDecision.ACCEPTED
    loaded = restarted.advise_realization_history_by_support_reference(claim.support_reference)
    assert loaded == _postgres_history(version=3)
    assert len(connection.rows["idea_advise_realization_history"]) == 1


def test_postgres_advise_history_rejects_owner_identity_conflict_without_mutation() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = _claim("fingerprint-a")
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=RECORDED_AT + timedelta(minutes=1),
        owner_receipt=DownstreamSubmissionOwnerReceipt(
            owner_authority=SourceSystem.LOTUS_ADVISE,
            owner_request_id="ipi_001",
            owner_realization_id="ipr_001",
            owner_work_id="iarw_001",
            source_event_version=1,
            source_evidence_fingerprint="sha256:downstream-evidence",
        ),
    )

    conflict = repository.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=replace(_postgres_history(version=2), realization_id="ipr_other"),
    )

    assert conflict.decision is AdviseRealizationHistoryMutationDecision.CONFLICT
    assert conflict.blocker == "advise_realization_owner_receipt_conflict"
    assert connection.rows["idea_advise_realization_history"] == []


def _postgres_history(*, version: int) -> AdviseProposalRealizationHistory:
    return replace(_history(version=version), conversion_intent_id="conversion-001")
