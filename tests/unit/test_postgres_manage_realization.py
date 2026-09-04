"""PostgreSQL parity for the Manage realization history (idea#675).

The durable path holds the same append-only compare-and-set the in-memory
reference enforces - across restart, replay, reopened-review appends, prefix
rewrites, receipt drift, and corrupt durable JSON.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    ManageActionRealizationHistory,
    ManageRealizationHistoryMutationDecision,
    SourceSystem,
)
from app.domain.downstream_submission import create_downstream_submission_claim
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_manage_realization import (
    _history_from_json,
    _history_to_json,
)
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_manage_realization_reconciliation import RECORDED_AT, _history
from tests.unit.test_postgres_downstream_submission import CLAIMED_AT


def test_postgres_manage_history_survives_restart_and_appends_monotonically() -> None:
    connection = FakePostgresConnection()
    repository = _repository_with_terminal_submission(connection)

    accepted = repository.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=_postgres_history(version=2),
    )
    restarted = PostgresIdeaRepository(connection)
    replayed = restarted.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=_postgres_history(version=2),
    )
    # The reopened review (APPROVED -> PENDING_REVIEW) is an ordinary
    # append in durable storage, exactly as the owner machine permits.
    reopened = restarted.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=_postgres_history(version=3),
    )
    rewritten = restarted.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=replace(
            _postgres_history(version=3),
            events=(
                _postgres_history(version=3).events[0],
                replace(_postgres_history(version=3).events[1], event_id="imae_rewritten"),
                _postgres_history(version=3).events[2],
            ),
        ),
    )

    assert accepted.decision is ManageRealizationHistoryMutationDecision.ACCEPTED
    assert accepted.appended_event_count == 2
    assert replayed.decision is ManageRealizationHistoryMutationDecision.REPLAYED
    assert replayed.appended_event_count == 0
    assert reopened.decision is ManageRealizationHistoryMutationDecision.ACCEPTED
    assert reopened.appended_event_count == 1
    assert rewritten.decision is ManageRealizationHistoryMutationDecision.CONFLICT
    assert rewritten.appended_event_count == 0
    assert rewritten.blocker == "manage_realization_history_conflict"
    loaded = restarted.manage_realization_history_by_support_reference(_SUPPORT_REFERENCE)
    assert loaded == _postgres_history(version=3)
    assert len(connection.rows["idea_manage_realization_history"]) == 1


def test_postgres_manage_history_rejects_owner_receipt_drift_without_mutation() -> None:
    connection = FakePostgresConnection()
    repository = _repository_with_terminal_submission(connection)

    conflict = repository.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=replace(_postgres_history(version=2), intake_id="iai_other"),
    )

    assert conflict.decision is ManageRealizationHistoryMutationDecision.CONFLICT
    assert conflict.blocker == "manage_realization_owner_receipt_conflict"
    assert connection.rows["idea_manage_realization_history"] == []


def test_postgres_manage_history_reports_missing_submission_without_writing() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)

    result = repository.persist_manage_realization_history(
        support_reference="downstream-submission-000000000000000000000000",
        history=_postgres_history(version=2),
    )

    assert result.decision is ManageRealizationHistoryMutationDecision.NOT_FOUND
    assert result.blocker == "downstream_submission_not_found"
    assert connection.rows["idea_manage_realization_history"] == []


def test_postgres_manage_history_rolls_back_compare_and_set_failure() -> None:
    connection = FakePostgresConnection()
    repository = _repository_with_terminal_submission(connection)
    repository.persist_manage_realization_history(
        support_reference=_SUPPORT_REFERENCE,
        history=_postgres_history(version=2),
    )
    connection.rows["idea_manage_realization_history"][0]["management_action_id"] = "corrupt"

    with pytest.raises(RuntimeError, match="compare-and-set failed"):
        repository.persist_manage_realization_history(
            support_reference=_SUPPORT_REFERENCE,
            history=_postgres_history(version=3),
        )

    assert connection.rollbacks == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda _payload: "not-an-object", "history_json must be an object"),
        (lambda payload: payload.update(events="not-an-array") or payload, "events"),
        (
            lambda payload: payload.update(management_action_id=" ") or payload,
            "management_action_id",
        ),
        (
            lambda payload: payload.update(source_event_version=True) or payload,
            "positive integer",
        ),
        (
            lambda payload: payload.update(rebalance_execution_proven="no") or payload,
            "must be boolean",
        ),
    ],
)
def test_postgres_manage_history_codec_rejects_corrupt_durable_evidence(
    mutate: Any,
    message: str,
) -> None:
    payload = _history_to_json(_postgres_history(version=2))

    with pytest.raises(ValueError, match=message):
        _history_from_json(mutate(payload))


_SUPPORT_REFERENCE = ""


def _repository_with_terminal_submission(
    connection: FakePostgresConnection,
) -> PostgresIdeaRepository:
    global _SUPPORT_REFERENCE
    repository = PostgresIdeaRepository(connection)
    claim = create_downstream_submission_claim(
        idempotency_key="submission-key-manage",
        request_fingerprint="fingerprint-manage",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-001",
        target=ConversionTarget.MANAGE_REVIEW,
        source_authority=SourceSystem.LOTUS_MANAGE,
        actor_subject="advisor-redacted",
        claimed_at_utc=CLAIMED_AT,
        lease_owner="downstream-submission",
        lease_attempt_id="attempt-submission-key-manage",
        lease_expires_at_utc=CLAIMED_AT + timedelta(minutes=5),
    )
    _SUPPORT_REFERENCE = claim.support_reference
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=RECORDED_AT + timedelta(minutes=1),
        owner_receipt=DownstreamSubmissionOwnerReceipt(
            owner_authority=SourceSystem.LOTUS_MANAGE,
            owner_request_id="iai_001",
            owner_realization_id="ima_001",
            owner_work_id="ima_001",
            source_event_version=1,
            source_evidence_fingerprint="sha256:aabbccddeeff",
        ),
    )
    return repository


def _postgres_history(*, version: int) -> ManageActionRealizationHistory:
    return replace(_history(version=version), conversion_intent_id="conversion-001")
