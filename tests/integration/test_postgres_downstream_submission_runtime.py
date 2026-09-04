from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import cast

import psycopg
import pytest
from psycopg.rows import dict_row

from app.domain import (
    AdviseRealizationHistoryMutationDecision,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    SourceSystem,
)
from app.infrastructure.postgres_repository import (
    PostgresConnection,
    PostgresIdeaRepository,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim
from tests.integration.postgres_runtime_support import (
    run_concurrent_repository_mutations,
    seed_active_conversion_resource,
)
from tests.unit.test_advise_realization_reconciliation import _history


SUBMITTED_AT = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


def test_postgres_downstream_submission_claim_recovery_and_restart_proof(
    postgres_database_url: str,
) -> None:
    candidate_id = seed_active_conversion_resource(
        postgres_database_url,
        "conversion-postgres-runtime",
    )
    barrier = Barrier(2)

    def claim_once() -> DownstreamSubmissionClaimDecision:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
            barrier.wait(timeout=5)
            return repository.claim_downstream_submission(
                _claim("concurrent-submission-key")
            ).decision

    with ThreadPoolExecutor(max_workers=2) as executor:
        decisions = tuple(executor.map(lambda _: claim_once(), range(2)))

    assert sorted(decisions) == sorted(
        (
            DownstreamSubmissionClaimDecision.ACCEPTED,
            DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED,
        )
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        finalized = repository.finalize_downstream_submission(
            idempotency_key="concurrent-submission-key",
            lease_owner="downstream-realization-test",
            lease_attempt_id="test-attempt-concurrent-submission-key",
            posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
            failure_reason="downstream_timeout",
        )
        assert finalized.decision is DownstreamSubmissionMutationDecision.ACCEPTED

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        pending = restarted.downstream_submissions_requiring_reconciliation(limit=10)
        assert len(pending) == 1
        candidate_submissions = restarted.downstream_submissions_for_candidate(candidate_id)
        assert [item.resource_id for item in candidate_submissions] == [
            "conversion-postgres-runtime"
        ]
        assert restarted.downstream_submissions_for_candidate("candidate-outside-scope") == ()
        support_reference = pending[0].support_reference
        accepted = restarted.reconcile_downstream_submission(
            support_reference=support_reference,
            resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
            actor_subject="platform-operator",
            reason="downstream_receipt_verified",
            change_reference="CHG-334-PG-001",
            reconciled_at_utc=SUBMITTED_AT + timedelta(minutes=2),
        )
        replayed = restarted.reconcile_downstream_submission(
            support_reference=support_reference,
            resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
            actor_subject="platform-operator",
            reason="downstream_receipt_verified",
            change_reference="CHG-334-PG-001",
            reconciled_at_utc=SUBMITTED_AT + timedelta(minutes=3),
        )
        assert accepted.decision is DownstreamSubmissionMutationDecision.ACCEPTED
        assert replayed.decision is DownstreamSubmissionMutationDecision.REPLAYED
        assert restarted.downstream_submissions_requiring_reconciliation(limit=10) == ()

    connection = psycopg.connect(postgres_database_url, row_factory=dict_row)
    interrupted = PostgresIdeaRepository(cast(PostgresConnection, connection))
    interrupted.claim_downstream_submission(_claim("interrupted-submission-key"))
    connection.close()
    with pytest.raises(psycopg.Error):
        interrupted.finalize_downstream_submission(
            idempotency_key="interrupted-submission-key",
            lease_owner="downstream-realization-test",
            lease_attempt_id="test-attempt-interrupted-submission-key",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
        )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        persisted = restarted.downstream_submission_by_idempotency_key("interrupted-submission-key")
        retry = restarted.claim_downstream_submission(_claim("interrupted-submission-key"))
        assert persisted is not None
        assert persisted.status is DownstreamSubmissionPosture.IN_FLIGHT
        assert retry.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED


def test_postgres_advise_history_race_reports_one_atomic_append_delta(
    postgres_database_url: str,
) -> None:
    conversion_intent_id = "conversion-atomic-history-delta"
    candidate_id = seed_active_conversion_resource(
        postgres_database_url,
        conversion_intent_id,
    )
    claim = build_downstream_submission_claim(
        idempotency_key="atomic-history-delta-submission",
        request_fingerprint="sha256:atomic-history-delta",
        resource_id=conversion_intent_id,
        submitted_at_utc=SUBMITTED_AT,
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.claim_downstream_submission(claim)
        repository.finalize_downstream_submission(
            idempotency_key=claim.idempotency_key,
            lease_owner=claim.lease_owner or "",
            lease_attempt_id=claim.lease_attempt_id or "",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
            owner_receipt=DownstreamSubmissionOwnerReceipt(
                owner_authority=SourceSystem.LOTUS_ADVISE,
                owner_request_id="ipi_001",
                owner_realization_id="ipr_001",
                owner_work_id="iarw_001",
                source_event_version=1,
                source_evidence_fingerprint="sha256:downstream-evidence",
            ),
        )

    history = replace(
        _history(version=2),
        idea_candidate_id=candidate_id,
        conversion_intent_id=conversion_intent_id,
    )
    results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, _worker_id: repository.persist_advise_realization_history(
            support_reference=claim.support_reference,
            history=history,
        ),
        ("writer-a", "writer-b"),
    )

    assert sorted((result.decision.value, result.appended_outcome_count) for result in results) == [
        (AdviseRealizationHistoryMutationDecision.ACCEPTED.value, 2),
        (AdviseRealizationHistoryMutationDecision.REPLAYED.value, 0),
    ]


def _claim(idempotency_key: str) -> DownstreamSubmissionRecord:
    return build_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint="sha256:postgres-downstream-runtime",
        resource_id="conversion-postgres-runtime",
        submitted_at_utc=SUBMITTED_AT,
    )
