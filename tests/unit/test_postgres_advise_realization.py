from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    SourceSystem,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_advise_realization import (
    _history_from_json,
    _history_to_json,
)
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
    final_outcomes = _postgres_history(version=3).outcomes
    conflict = restarted.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=replace(
            _postgres_history(version=3),
            outcomes=(
                *final_outcomes[:-1],
                replace(final_outcomes[-1], reason_code="different_completion"),
            ),
        ),
    )

    assert accepted.decision is AdviseRealizationHistoryMutationDecision.ACCEPTED
    assert accepted.appended_outcome_count == 2
    assert replayed.decision is AdviseRealizationHistoryMutationDecision.REPLAYED
    assert replayed.appended_outcome_count == 0
    assert progressed.decision is AdviseRealizationHistoryMutationDecision.ACCEPTED
    assert progressed.appended_outcome_count == 1
    assert conflict.decision is AdviseRealizationHistoryMutationDecision.CONFLICT
    assert conflict.appended_outcome_count == 0
    assert conflict.blocker == "advise_realization_history_conflict"
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


def test_postgres_advise_history_reports_missing_submission_without_writing() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)

    result = repository.persist_advise_realization_history(
        support_reference="downstream-submission-000000000000000000000000",
        history=_postgres_history(version=2),
    )

    assert result.decision is AdviseRealizationHistoryMutationDecision.NOT_FOUND
    assert result.blocker == "downstream_submission_not_found"
    assert connection.rows["idea_advise_realization_history"] == []


def test_postgres_advise_history_rolls_back_compare_and_set_failure() -> None:
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
    repository.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=_postgres_history(version=2),
    )
    connection.rows["idea_advise_realization_history"][0]["realization_id"] = "corrupt"

    with pytest.raises(RuntimeError, match="compare-and-set failed"):
        repository.persist_advise_realization_history(
            support_reference=claim.support_reference,
            history=_postgres_history(version=3),
        )

    assert connection.rollbacks == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda _payload: "not-an-object", "history_json must be an object"),
        (lambda payload: payload.update(outcomes="not-an-array") or payload, "outcomes"),
        (lambda payload: payload.update(realization_id=" ") or payload, "realization_id"),
        (
            lambda payload: payload.update(current_source_event_version=True) or payload,
            "positive integer",
        ),
        (
            lambda payload: payload.update(proposal_record_created="yes") or payload,
            "must be boolean",
        ),
    ],
)
def test_postgres_advise_history_codec_rejects_corrupt_durable_evidence(
    mutate: Any,
    message: str,
) -> None:
    payload = _history_to_json(_postgres_history(version=2))

    with pytest.raises(ValueError, match=message):
        _history_from_json(mutate(payload))


def _postgres_history(*, version: int) -> AdviseProposalRealizationHistory:
    return replace(_history(version=version), conversion_intent_id="conversion-001")
