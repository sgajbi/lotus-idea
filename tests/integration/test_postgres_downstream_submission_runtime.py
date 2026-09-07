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
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationDecision,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    SourceSystem,
    QueueAccessScopeFilter,
)
from app.application.advise_realization_reconciliation import (
    AdviseRealizationReconciliationStatus,
    ReconcileAdviseRealizationCommand,
    reconcile_advise_realization_history,
)
from app.domain.advise_evidence_identity import (
    advise_source_evidence_fingerprint,
)
from app.ports.downstream_realization import DownstreamRealizationNotObserved
from app.infrastructure.postgres_repository import (
    PostgresConnection,
    PostgresIdeaRepository,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim
from tests.integration.postgres_runtime_support import (
    run_concurrent_repository_mutations,
    seed_active_conversion_resource,
    seed_governed_advise_conversion_resource,
    table_count,
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
    concurrent_claim = _claim("concurrent-submission-key")
    barrier = Barrier(2)

    def claim_once() -> DownstreamSubmissionClaimDecision:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
            barrier.wait(timeout=5)
            return repository.claim_downstream_submission(concurrent_claim).decision

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
            tenant_id="tenant-private-bank-sg",
            idempotency_key="concurrent-submission-key",
            lease_owner="downstream-realization-test",
            lease_attempt_id=concurrent_claim.lease_attempt_id or "",
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
    interrupted_claim = _claim("interrupted-submission-key")
    interrupted.claim_downstream_submission(interrupted_claim)
    connection.close()
    with pytest.raises(psycopg.Error):
        interrupted.finalize_downstream_submission(
            tenant_id="tenant-private-bank-sg",
            idempotency_key="interrupted-submission-key",
            lease_owner="downstream-realization-test",
            lease_attempt_id=interrupted_claim.lease_attempt_id or "",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
        )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        persisted = restarted.downstream_submission_by_idempotency_key(
            "tenant-private-bank-sg", "interrupted-submission-key"
        )
        retry = restarted.claim_downstream_submission(_claim("interrupted-submission-key"))
        assert persisted is not None
        assert persisted.status is DownstreamSubmissionPosture.IN_FLIGHT
        assert retry.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED


def test_postgres_downstream_submission_identity_is_tenant_scoped(
    postgres_database_url: str,
) -> None:
    shared_key = "tenant-scoped-postgres-submission-key"
    first_resource = "conversion-tenant-scope-sg"
    second_resource = "conversion-tenant-scope-hk"
    seed_active_conversion_resource(postgres_database_url, first_resource)
    seed_active_conversion_resource(
        postgres_database_url,
        second_resource,
        tenant_id="tenant-private-bank-hk",
    )
    first = build_downstream_submission_claim(
        tenant_id="tenant-private-bank-sg",
        idempotency_key=shared_key,
        request_fingerprint="sha256:tenant-scope-sg",
        resource_id=first_resource,
        submitted_at_utc=SUBMITTED_AT,
    )
    second = build_downstream_submission_claim(
        tenant_id="tenant-private-bank-hk",
        idempotency_key=shared_key,
        request_fingerprint="sha256:tenant-scope-hk",
        resource_id=second_resource,
        submitted_at_utc=SUBMITTED_AT,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        first_result = repository.claim_downstream_submission(first)
        second_result = repository.claim_downstream_submission(second)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        persisted_first = restarted.downstream_submission_by_idempotency_key(
            first.tenant_id, shared_key
        )
        persisted_second = restarted.downstream_submission_by_idempotency_key(
            second.tenant_id, shared_key
        )

    assert first_result.decision is DownstreamSubmissionClaimDecision.ACCEPTED
    assert second_result.decision is DownstreamSubmissionClaimDecision.ACCEPTED
    assert persisted_first == first
    assert persisted_second == second
    assert first.support_reference != second.support_reference
    assert first.lease_attempt_id != second.lease_attempt_id


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
    history = replace(
        _history(version=2),
        idea_candidate_id=candidate_id,
        conversion_intent_id=conversion_intent_id,
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.claim_downstream_submission(claim)
        repository.finalize_downstream_submission(
            tenant_id="tenant-private-bank-sg",
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
                source_evidence_fingerprint=history.source_evidence_fingerprint,
            ),
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


def test_postgres_advise_reconciliation_is_one_time_and_exact_replay_is_zero_delta(
    postgres_database_url: str,
) -> None:
    conversion_intent_id = "conversion-advise-restart-reconciliation"
    candidate_id, evidence_fingerprint = seed_governed_advise_conversion_resource(
        postgres_database_url,
        conversion_intent_id,
    )
    claim = build_downstream_submission_claim(
        idempotency_key="advise-restart-reconciliation-submission",
        request_fingerprint="sha256:advise-restart-reconciliation",
        resource_id=conversion_intent_id,
        submitted_at_utc=SUBMITTED_AT,
    )
    owner_evidence_fingerprint = advise_source_evidence_fingerprint(
        candidate_id=candidate_id,
        evidence_content_hash=evidence_fingerprint,
    )
    owner_history = replace(
        _history(version=3),
        idea_candidate_id=candidate_id,
        conversion_intent_id=conversion_intent_id,
        source_evidence_fingerprint=owner_evidence_fingerprint,
    )

    class RetainedOwnerHistoryReader:
        call_count = 0

        def load_proposal_realization(self, **_: object) -> AdviseProposalRealizationHistory:
            self.call_count += 1
            return owner_history

        def load_realization_by_conversion_intent(
            self, **_: object
        ) -> AdviseProposalRealizationHistory:
            raise AssertionError("the retained owner receipt must remain the lookup identity")

    reader = RetainedOwnerHistoryReader()
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.claim_downstream_submission(claim)
        repository.finalize_downstream_submission(
            tenant_id="tenant-private-bank-sg",
            idempotency_key=claim.idempotency_key,
            lease_owner=claim.lease_owner or "",
            lease_attempt_id=claim.lease_attempt_id or "",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
            owner_receipt=DownstreamSubmissionOwnerReceipt(
                owner_authority=SourceSystem.LOTUS_ADVISE,
                owner_request_id=owner_history.intake_id,
                owner_realization_id=owner_history.realization_id,
                owner_work_id=owner_history.review_work_id,
                source_event_version=1,
                source_evidence_fingerprint=owner_evidence_fingerprint,
            ),
        )

    command = ReconcileAdviseRealizationCommand(
        support_reference=claim.support_reference,
        actor_subject="platform-operator",
        access_scope_filter=QueueAccessScopeFilter(
            tenant_id="tenant-sg",
            book_id="book-private-bank-sg",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            client_id="client-redacted",
        ),
        accepted_at_utc=SUBMITTED_AT + timedelta(minutes=2),
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as first_connection:
        first_runtime = PostgresIdeaRepository(cast(PostgresConnection, first_connection))
        first = reconcile_advise_realization_history(
            command,
            repository=first_runtime,
            advise_reader=reader,
        )
        persisted_after_first = first_runtime.advise_realization_history_by_support_reference(
            claim.support_reference
        )
        submission_after_first = first_runtime.downstream_submission_by_support_reference(
            claim.support_reference
        )

    governed_tables = {
        "idea_advise_realization_history",
        "idea_audit_event",
        "idea_downstream_submission",
        "idea_outbox_event",
    }
    counts_after_first = {
        table: table_count(postgres_database_url, table, allowed_tables=governed_tables)
        for table in governed_tables
    }
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as replay_connection:
        reconstructed_runtime = PostgresIdeaRepository(cast(PostgresConnection, replay_connection))
        replay = reconcile_advise_realization_history(
            command,
            repository=reconstructed_runtime,
            advise_reader=reader,
        )
        persisted_after_replay = (
            reconstructed_runtime.advise_realization_history_by_support_reference(
                claim.support_reference
            )
        )
        submission_after_replay = reconstructed_runtime.downstream_submission_by_support_reference(
            claim.support_reference
        )

    assert first.status is AdviseRealizationReconciliationStatus.ACCEPTED
    assert first.appended_outcome_count == 3
    assert replay.status is AdviseRealizationReconciliationStatus.REPLAYED
    assert replay.appended_outcome_count == 0
    assert persisted_after_first == owner_history
    assert persisted_after_replay == persisted_after_first
    assert submission_after_first == submission_after_replay
    assert submission_after_replay is not None
    assert submission_after_replay.attempt_count == 1
    assert submission_after_replay.owner_receipt is not None
    assert submission_after_replay.owner_receipt.owner_request_id == owner_history.intake_id
    assert (
        submission_after_replay.owner_receipt.owner_realization_id == owner_history.realization_id
    )
    assert submission_after_replay.owner_receipt.owner_work_id == owner_history.review_work_id
    assert reader.call_count == 2
    assert {
        table: table_count(postgres_database_url, table, allowed_tables=governed_tables)
        for table in governed_tables
    } == counts_after_first


def test_postgres_precommit_timeout_recovery_preserves_one_attempt_and_zero_owner_progress(
    postgres_database_url: str,
) -> None:
    conversion_intent_id = "conversion-precommit-timeout"
    candidate_id, _ = seed_governed_advise_conversion_resource(
        postgres_database_url,
        conversion_intent_id,
    )

    claim = build_downstream_submission_claim(
        idempotency_key="precommit-timeout-submission",
        request_fingerprint="sha256:precommit-timeout",
        resource_id=conversion_intent_id,
        submitted_at_utc=SUBMITTED_AT,
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as submission_connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, submission_connection))
        repository.claim_downstream_submission(claim)
        repository.finalize_downstream_submission(
            tenant_id="tenant-private-bank-sg",
            idempotency_key=claim.idempotency_key,
            lease_owner=claim.lease_owner or "",
            lease_attempt_id=claim.lease_attempt_id or "",
            posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
            failure_reason="downstream_timeout",
        )

    class OwnerAbsenceReader:
        recovery_calls = 0

        def load_realization_by_conversion_intent(
            self, **_: object
        ) -> AdviseProposalRealizationHistory:
            self.recovery_calls += 1
            raise DownstreamRealizationNotObserved("owner acceptance not observed")

        def load_proposal_realization(self, **_: object) -> AdviseProposalRealizationHistory:
            raise AssertionError("recovery without a receipt must use conversion intent identity")

    reader = OwnerAbsenceReader()
    governed_tables = {"idea_audit_event", "idea_outbox_event"}
    counts_before = {
        table: table_count(
            postgres_database_url,
            table,
            allowed_tables=governed_tables,
        )
        for table in governed_tables
    }
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as restart_connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, restart_connection))
        before = restarted.downstream_submission_by_support_reference(claim.support_reference)
        assert before is not None

        result = reconcile_advise_realization_history(
            ReconcileAdviseRealizationCommand(
                support_reference=claim.support_reference,
                actor_subject="platform-operator",
                access_scope_filter=QueueAccessScopeFilter(tenant_id="tenant-sg"),
                accepted_at_utc=SUBMITTED_AT + timedelta(minutes=2),
            ),
            repository=restarted,
            advise_reader=reader,
        )

        after = restarted.downstream_submission_by_support_reference(claim.support_reference)
        history = restarted.advise_realization_history_by_support_reference(claim.support_reference)

    assert result.status is AdviseRealizationReconciliationStatus.OWNER_ACCEPTANCE_NOT_OBSERVED
    assert result.appended_outcome_count == 0
    assert before.attempt_count == 1
    assert after == before
    assert after.owner_receipt is None
    assert history is None
    assert reader.recovery_calls == 1
    assert {
        table: table_count(
            postgres_database_url,
            table,
            allowed_tables=governed_tables,
        )
        for table in governed_tables
    } == counts_before


def _claim(idempotency_key: str) -> DownstreamSubmissionRecord:
    return build_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint="sha256:postgres-downstream-runtime",
        resource_id="conversion-postgres-runtime",
        submitted_at_utc=SUBMITTED_AT,
    )
