from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import cast

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationDecision,
    ConversionTarget,
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
from app.ports.downstream_realization import DownstreamRealizationNotObserved
from app.domain.evidence_hashing import evidence_hash_for_candidate
from app.infrastructure.postgres_repository import (
    PostgresConnection,
    PostgresIdeaRepository,
)
from app.infrastructure.postgres_codecs import (
    conversion_intent_to_json,
    idea_candidate_to_json,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim
from tests.integration.postgres_runtime_support import (
    run_concurrent_repository_mutations,
    seed_active_conversion_resource,
    table_count,
)
from tests.unit.test_advise_realization_reconciliation import _history
from tests.unit.test_downstream_realization_application import (
    candidate,
    repository_with_conversion,
)


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


def test_postgres_advise_reconciliation_is_one_time_and_exact_replay_is_zero_delta(
    postgres_database_url: str,
) -> None:
    conversion_intent_id = "conversion-advise-restart-reconciliation"
    candidate_id, evidence_fingerprint = _seed_governed_advise_conversion_resource(
        postgres_database_url,
        conversion_intent_id,
    )
    claim = build_downstream_submission_claim(
        idempotency_key="advise-restart-reconciliation-submission",
        request_fingerprint="sha256:advise-restart-reconciliation",
        resource_id=conversion_intent_id,
        submitted_at_utc=SUBMITTED_AT,
    )
    owner_history = replace(
        _history(version=3),
        idea_candidate_id=candidate_id,
        conversion_intent_id=conversion_intent_id,
        source_evidence_fingerprint=evidence_fingerprint,
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
                source_evidence_fingerprint=evidence_fingerprint,
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
    candidate_id, _ = _seed_governed_advise_conversion_resource(
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


def _seed_governed_advise_conversion_resource(
    postgres_database_url: str,
    conversion_intent_id: str,
) -> tuple[str, str]:
    candidate_id = seed_active_conversion_resource(postgres_database_url, conversion_intent_id)
    candidate_value = candidate(candidate_id)
    fixture_repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    fixture_record = fixture_repository.snapshot().candidate_records["idea-downstream-001"]
    fixture_intent = fixture_record.conversion_intents[0]
    conversion_intent = replace(
        fixture_intent,
        intent=replace(
            fixture_intent.intent,
            conversion_intent_id=conversion_intent_id,
            candidate_id=candidate_id,
        ),
        evidence_packet_id=candidate_value.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate_value.evidence_packet.lineage_ref.content_hash,
        source_revision_vector_digest=(
            candidate_value.evidence_packet.source_revision_vector_digest
        ),
        source_cut_posture=candidate_value.evidence_packet.source_cut_posture,
        source_signal_ids=candidate_value.source_signal_ids,
        review_authority_grant=None,
    )
    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE idea_candidate_record
            SET evidence_packet_id = %s,
                evidence_hash = %s,
                candidate_json = %s,
                business_identity_id = %s,
                identity_policy_version = %s,
                material_fingerprint = %s,
                material_version = %s,
                evidence_version = %s,
                change_reason = %s,
                supersedes_material_version = %s
            WHERE candidate_id = %s
            """,
            (
                candidate_value.evidence_packet.evidence_packet_id,
                evidence_hash_for_candidate(candidate_value),
                Jsonb(idea_candidate_to_json(candidate_value)),
                candidate_value.identity.business_identity_id,
                candidate_value.identity.policy_version,
                candidate_value.identity.material_fingerprint,
                candidate_value.identity.material_version,
                candidate_value.identity.evidence_version,
                candidate_value.identity.change_reason.value,
                candidate_value.identity.supersedes_material_version,
                candidate_id,
            ),
        )
        cursor.execute(
            """
            UPDATE idea_conversion_intent
            SET intent_json = %s
            WHERE conversion_intent_id = %s
            """,
            (Jsonb(conversion_intent_to_json(conversion_intent)), conversion_intent_id),
        )
    return candidate_id, conversion_intent.evidence_content_hash


def _claim(idempotency_key: str) -> DownstreamSubmissionRecord:
    return build_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint="sha256:postgres-downstream-runtime",
        resource_id="conversion-postgres-runtime",
        submitted_at_utc=SUBMITTED_AT,
    )
