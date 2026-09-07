from dataclasses import replace

import pytest

from app.application.candidate_lookup import candidate_tenant_id
from app.application.review_workflow import (
    ApplyReviewActionToRepositoryCommand,
    apply_review_action_to_repository,
)
from app.domain import CandidatePersistenceDecision, InMemoryIdeaRepository
from app.domain import (
    CandidateEvidenceIdentity,
    ConversionPersistenceDecision,
    EvidencePackPersistenceDecision,
    IdeaLifecycleStatus,
    ReviewAccessScope,
    ReviewAction,
    ReviewPersistenceDecision,
    ReviewPosture,
    UnscopedCandidatePersistenceError,
    request_report_evidence_pack,
)
from app.domain.idempotency import (
    IdempotencyDecision,
    system_scoped_idempotency_identity,
    tenant_scoped_idempotency_identity,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_idea_persistence import (
    EVALUATED_AT,
    conversion_intent_command,
    high_cash_candidate,
    report_evidence_pack_command,
    request_conversion_intent,
    with_persisted_review_authority,
)
from tests.unit.test_review_workflow_application import (
    advisor_context,
    decision_command,
    presentation_receipt,
    review_candidate,
)


def test_candidate_idempotency_namespace_is_tenant_scoped_and_restart_safe() -> None:
    repository = InMemoryIdeaRepository()
    tenant_a, _ = high_cash_candidate(tenant_id="tenant-a")
    tenant_b, _ = high_cash_candidate(tenant_id="tenant-b")
    shared_key = "candidate:shared-client-key"
    payload_a = {"candidateId": tenant_a.candidate_id}
    payload_b = {"candidateId": tenant_b.candidate_id}

    accepted_a = repository.persist_candidate(
        tenant_a,
        idempotency_key=shared_key,
        payload=payload_a,
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    accepted_b = repository.persist_candidate(
        tenant_b,
        idempotency_key=shared_key,
        payload=payload_b,
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    recovered = InMemoryIdeaRepository(repository.snapshot())

    replayed_a = recovered.persist_candidate(
        tenant_a,
        idempotency_key=shared_key,
        payload=payload_a,
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    replayed_b = recovered.persist_candidate(
        tenant_b,
        idempotency_key=shared_key,
        payload=payload_b,
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert accepted_a.decision is CandidatePersistenceDecision.ACCEPTED
    assert accepted_b.decision is CandidatePersistenceDecision.ACCEPTED
    assert replayed_a.decision is CandidatePersistenceDecision.REPLAYED
    assert replayed_b.decision is CandidatePersistenceDecision.REPLAYED
    assert replayed_a.record is not None
    assert replayed_a.record.candidate.candidate_id == tenant_a.candidate_id
    assert replayed_b.record is not None
    assert replayed_b.record.candidate.candidate_id == tenant_b.candidate_id
    assert set(recovered.snapshot().idempotency_records) >= {
        tenant_scoped_idempotency_identity("tenant-a", shared_key),
        tenant_scoped_idempotency_identity("tenant-b", shared_key),
    }


def test_system_and_tenant_idempotency_namespaces_cannot_collide() -> None:
    repository = InMemoryIdeaRepository()
    candidate, _ = high_cash_candidate(tenant_id="tenant-a")
    tenant_key = "candidate:shared-client-key"
    system_key = tenant_scoped_idempotency_identity("tenant-a", tenant_key)

    accepted_candidate = repository.persist_candidate(
        candidate,
        idempotency_key=tenant_key,
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    accepted_system = repository.record_outbox_delivery_run_request(
        idempotency_key=system_key,
        payload={"maxEvents": 25},
    )
    replayed_system = repository.record_outbox_delivery_run_request(
        idempotency_key=system_key,
        payload={"maxEvents": 25},
    )

    assert accepted_candidate.decision is CandidatePersistenceDecision.ACCEPTED
    assert accepted_system is IdempotencyDecision.ACCEPTED
    assert replayed_system is IdempotencyDecision.REPLAYED
    assert len(repository.snapshot().idempotency_records) == 2


def test_postgres_snapshot_preserves_system_idempotency_replay_identity() -> None:
    source = PostgresIdeaRepository(FakePostgresConnection())
    raw_key = "outbox-delivery-run:shared-client-key"
    payload = {"maxEvents": 25}

    accepted = source.record_outbox_delivery_run_request(
        idempotency_key=raw_key,
        payload=payload,
    )
    snapshot = source.snapshot()
    restored = InMemoryIdeaRepository(snapshot)
    replayed = restored.record_outbox_delivery_run_request(
        idempotency_key=raw_key,
        payload=payload,
    )

    assert accepted is IdempotencyDecision.ACCEPTED
    assert set(snapshot.idempotency_records) == {system_scoped_idempotency_identity(raw_key)}
    assert replayed is IdempotencyDecision.REPLAYED


def test_idempotency_namespaces_refuse_missing_authority_and_raw_keys() -> None:
    repository = InMemoryIdeaRepository()
    candidate, _ = high_cash_candidate(tenant_id="tenant-a")
    accepted = repository.persist_candidate(
        candidate,
        idempotency_key="candidate:retained-scope",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert accepted.record is not None
    unscoped_record = replace(
        accepted.record,
        candidate=replace(accepted.record.candidate, access_scope=None),
    )

    with pytest.raises(ValueError, match="persisted candidate tenant scope is unavailable"):
        candidate_tenant_id(unscoped_record)
    with pytest.raises(ValueError, match="idempotency_key is required"):
        repository.record_outbox_delivery_run_request(idempotency_key=" ", payload={})
    with pytest.raises(ValueError, match="idempotency_key must be non-empty"):
        system_scoped_idempotency_identity(" ")

    retained = InMemoryIdeaRepository(
        replace(
            repository.snapshot(),
            candidate_records={candidate.candidate_id: unscoped_record},
        )
    )
    with pytest.raises(
        UnscopedCandidatePersistenceError,
        match="persisted candidate tenant scope is unavailable",
    ):
        retained.record_lifecycle_transition(
            candidate.candidate_id,
            IdeaLifecycleStatus.ENRICHED,
            idempotency_key="lifecycle:retained-unscoped",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="lifecycle-worker",
            occurred_at_utc=EVALUATED_AT,
        )


def test_conversion_and_report_mutations_reuse_raw_key_independently_by_tenant() -> None:
    repository = InMemoryIdeaRepository()
    candidate_a, _ = high_cash_candidate(tenant_id="tenant-a")
    candidate_b, _ = high_cash_candidate(tenant_id="tenant-b")
    candidate_a = replace(
        candidate_a,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    candidate_b = replace(
        candidate_b,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    for candidate in (candidate_a, candidate_b):
        result = repository.persist_candidate(
            candidate,
            idempotency_key=f"candidate:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
        assert result.decision is CandidatePersistenceDecision.ACCEPTED
        repository = with_persisted_review_authority(repository, candidate)

    shared_conversion_key = "conversion:shared-client-key"
    base_conversion = conversion_intent_command()
    command_a = replace(
        base_conversion,
        conversion_intent_id="conversion-tenant-a",
        idempotency_key=shared_conversion_key,
        expected_candidate_evidence=base_conversion.expected_candidate_evidence.from_candidate(
            candidate_a
        ),
    )
    command_b = replace(
        base_conversion,
        conversion_intent_id="conversion-tenant-b",
        idempotency_key=shared_conversion_key,
        expected_candidate_evidence=base_conversion.expected_candidate_evidence.from_candidate(
            candidate_b
        ),
    )
    conversion_a = request_conversion_intent(candidate_a, command_a)
    conversion_b = request_conversion_intent(candidate_b, command_b)
    persisted_conversion_a = repository.record_conversion_intent(
        conversion_a,
        idempotency_key=shared_conversion_key,
        payload={"candidateId": candidate_a.candidate_id},
    )
    persisted_conversion_b = repository.record_conversion_intent(
        conversion_b,
        idempotency_key=shared_conversion_key,
        payload={"candidateId": candidate_b.candidate_id},
    )

    shared_report_key = "report:shared-client-key"
    base_pack = report_evidence_pack_command()
    pack_a = replace(
        base_pack,
        report_evidence_pack_id="report-pack-tenant-a",
        idempotency_key=shared_report_key,
    )
    pack_b = replace(
        base_pack,
        report_evidence_pack_id="report-pack-tenant-b",
        idempotency_key=shared_report_key,
    )
    report_a = request_report_evidence_pack(
        conversion_a.candidate,
        conversion_a.conversion_intent,
        pack_a,
    )
    report_b = request_report_evidence_pack(
        conversion_b.candidate,
        conversion_b.conversion_intent,
        pack_b,
    )
    persisted_report_a = repository.record_report_evidence_pack(
        report_a,
        idempotency_key=shared_report_key,
        payload={"candidateId": candidate_a.candidate_id},
    )
    persisted_report_b = repository.record_report_evidence_pack(
        report_b,
        idempotency_key=shared_report_key,
        payload={"candidateId": candidate_b.candidate_id},
    )

    assert persisted_conversion_a.decision is ConversionPersistenceDecision.ACCEPTED
    assert persisted_conversion_b.decision is ConversionPersistenceDecision.ACCEPTED
    assert persisted_report_a.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert persisted_report_b.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert len(repository.snapshot().idempotency_records) == 6


def test_review_mutation_reuses_raw_key_independently_by_tenant() -> None:
    repository = InMemoryIdeaRepository()
    candidate_a = review_candidate("review-tenant-a")
    candidate_b = replace(
        review_candidate("review-tenant-b"),
        access_scope=ReviewAccessScope(
            tenant_id="tenant-private-bank-hk",
            book_id="book-advisor-hk",
            portfolio_id="PB_HK_GLOBAL_BAL_001",
            client_id="client-hk-001",
        ),
    )
    receipt_a = replace(
        presentation_receipt(candidate_a),
        receipt_id="receipt-review-tenant-a",
    )
    receipt_b = replace(
        presentation_receipt(candidate_b),
        receipt_id="receipt-review-tenant-b",
    )
    for candidate, receipt in ((candidate_a, receipt_a), (candidate_b, receipt_b)):
        persisted = repository.persist_candidate(
            candidate,
            idempotency_key=f"candidate:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )
        assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
        assert repository.record_presentation_receipt(receipt).receipt is not None

    shared_key = "review:shared-client-key"
    command_a = ApplyReviewActionToRepositoryCommand(
        candidate_id=candidate_a.candidate_id,
        review=replace(
            decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
            review_id="review-decision-tenant-a",
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate_a),
            presentation_receipt_id=receipt_a.receipt_id,
        ),
        idempotency_key=shared_key,
        accepted_at_utc=receipt_a.accepted_at_utc,
    )
    hk_actor = replace(
        advisor_context(),
        tenant_ids=frozenset({"tenant-private-bank-hk"}),
        book_ids=frozenset({"book-advisor-hk"}),
        portfolio_ids=frozenset({"PB_HK_GLOBAL_BAL_001"}),
        client_ids=frozenset({"client-hk-001"}),
    )
    command_b = ApplyReviewActionToRepositoryCommand(
        candidate_id=candidate_b.candidate_id,
        review=replace(
            decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
            review_id="review-decision-tenant-b",
            actor=hk_actor,
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate_b),
            presentation_receipt_id=receipt_b.receipt_id,
        ),
        idempotency_key=shared_key,
        accepted_at_utc=receipt_b.accepted_at_utc,
    )

    accepted_a = apply_review_action_to_repository(command_a, repository=repository)
    accepted_b = apply_review_action_to_repository(command_b, repository=repository)
    recovered = InMemoryIdeaRepository(repository.snapshot())
    replayed_a = apply_review_action_to_repository(command_a, repository=recovered)
    replayed_b = apply_review_action_to_repository(command_b, repository=recovered)

    assert accepted_a.persistence.decision is ReviewPersistenceDecision.ACCEPTED
    assert accepted_b.persistence.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed_a.persistence.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed_b.persistence.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed_a.require_review_decision().candidate_id == candidate_a.candidate_id
    assert replayed_b.require_review_decision().candidate_id == candidate_b.candidate_id
