from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from app.application.persisted_action_evidence import PersistedActionEvidenceUnavailable
from app.application.report_evidence import (
    ReportEvidencePackWorkflowResult,
    RequestReportEvidencePackToRepositoryCommand,
    request_report_evidence_pack_to_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    InMemoryIdeaRepository,
    ReviewAccessScope,
)
from tests.unit.test_report_evidence import (
    EVALUATED_AT,
    candidate,
    command as report_evidence_command,
    report_conversion_intent,
)
from tests.support.review_authority import with_in_memory_review_authority


def _repository_with_report_conversion_intent() -> tuple[InMemoryIdeaRepository, str]:
    repository = InMemoryIdeaRepository()
    source_candidate = replace(
        candidate(),
        access_scope=ReviewAccessScope(
            tenant_id="tenant-a",
            book_id="book-advisor-001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            client_id="client-001",
        ),
    )
    persisted = repository.persist_candidate(
        source_candidate,
        idempotency_key="signal-ingestion:report-evidence-workflow:001",
        payload={"candidate_id": source_candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
    repository = with_in_memory_review_authority(
        repository,
        source_candidate,
        accepted_at_utc=EVALUATED_AT,
    )
    conversion_result = report_conversion_intent(source_candidate)
    conversion_intent = conversion_result.conversion_intent
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_intent.idempotency_key,
        payload={
            "candidate_id": source_candidate.candidate_id,
            "target": conversion_intent.intent.target.value,
        },
    )
    return repository, conversion_intent.intent.conversion_intent_id


def _request_command(
    conversion_intent_id: str,
) -> RequestReportEvidencePackToRepositoryCommand:
    evidence_pack = report_evidence_command()
    return RequestReportEvidencePackToRepositoryCommand(
        conversion_intent_id=conversion_intent_id,
        evidence_pack=evidence_pack,
        idempotency_key=evidence_pack.idempotency_key,
    )


def test_report_evidence_replay_returns_exact_persisted_pack_without_side_effects() -> None:
    repository, conversion_intent_id = _repository_with_report_conversion_intent()
    request = _request_command(conversion_intent_id)

    accepted = request_report_evidence_pack_to_repository(request, repository=repository)
    before_replay = repository.snapshot()
    replayed = request_report_evidence_pack_to_repository(request, repository=repository)
    after_replay = repository.snapshot()

    assert accepted.persistence.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert accepted.report_evidence_pack is not None
    assert accepted.persistence.record is not None
    assert accepted.report_evidence_pack is accepted.persistence.record.report_evidence_packs[-1]
    assert replayed.persistence.decision is EvidencePackPersistenceDecision.REPLAYED
    assert replayed.report_evidence_pack == accepted.report_evidence_pack
    assert replayed.persistence.record is not None
    assert replayed.report_evidence_pack is replayed.persistence.record.report_evidence_packs[-1]
    assert after_replay.candidate_records == before_replay.candidate_records
    assert after_replay.outbox_events == before_replay.outbox_events


def test_report_evidence_replay_rejects_client_publication_escalation() -> None:
    repository, conversion_intent_id = _repository_with_report_conversion_intent()
    request = _request_command(conversion_intent_id)
    accepted = request_report_evidence_pack_to_repository(request, repository=repository)
    escalated_request = replace(
        request,
        evidence_pack=replace(
            request.evidence_pack,
            client_ready_publication_requested=True,
        ),
    )

    conflicted = request_report_evidence_pack_to_repository(
        escalated_request,
        repository=repository,
    )

    assert accepted.persistence.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert conflicted.persistence.decision is EvidencePackPersistenceDecision.CONFLICT
    assert conflicted.report_evidence_pack is None


def test_report_evidence_replay_fails_closed_when_persisted_pack_is_missing() -> None:
    repository, conversion_intent_id = _repository_with_report_conversion_intent()
    record = repository.candidate_record_for_conversion_intent(conversion_intent_id)
    assert record is not None
    replay_repository = PrecheckedReportEvidenceRepository(
        repository,
        EvidencePackPersistenceResult(
            decision=EvidencePackPersistenceDecision.REPLAYED,
            record=record,
        ),
    )

    with pytest.raises(PersistedActionEvidenceUnavailable, match="exactly one persisted action"):
        request_report_evidence_pack_to_repository(
            _request_command(conversion_intent_id),
            repository=replay_repository,
        )


def test_report_evidence_success_fails_closed_without_candidate_record() -> None:
    repository, conversion_intent_id = _repository_with_report_conversion_intent()
    replay_repository = PrecheckedReportEvidenceRepository(
        repository,
        EvidencePackPersistenceResult(
            decision=EvidencePackPersistenceDecision.REPLAYED,
            record=None,
        ),
    )

    with pytest.raises(PersistedActionEvidenceUnavailable, match="no candidate record"):
        request_report_evidence_pack_to_repository(
            _request_command(conversion_intent_id),
            repository=replay_repository,
        )


def test_report_evidence_replay_fails_closed_when_persisted_pack_is_ambiguous() -> None:
    repository, conversion_intent_id = _repository_with_report_conversion_intent()
    request = _request_command(conversion_intent_id)
    accepted = request_report_evidence_pack_to_repository(request, repository=repository)
    assert accepted.persistence.record is not None
    assert accepted.report_evidence_pack is not None
    ambiguous_record = replace(
        accepted.persistence.record,
        report_evidence_packs=(
            accepted.report_evidence_pack,
            accepted.report_evidence_pack,
        ),
    )
    replay_repository = PrecheckedReportEvidenceRepository(
        repository,
        EvidencePackPersistenceResult(
            decision=EvidencePackPersistenceDecision.REPLAYED,
            record=ambiguous_record,
        ),
    )

    with pytest.raises(PersistedActionEvidenceUnavailable, match="exactly one persisted action"):
        request_report_evidence_pack_to_repository(request, repository=replay_repository)


def test_report_evidence_success_result_guard_rejects_missing_evidence() -> None:
    with pytest.raises(PersistedActionEvidenceUnavailable, match="no persisted evidence pack"):
        ReportEvidencePackWorkflowResult(
            report_evidence_pack=None,
            persistence=EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.REPLAYED,
                record=None,
            ),
        ).require_report_evidence_pack()


def test_report_evidence_command_rejects_mismatched_idempotency_boundary() -> None:
    with pytest.raises(ValueError, match="idempotency key must match"):
        RequestReportEvidencePackToRepositoryCommand(
            conversion_intent_id="conversion-report-evidence-001",
            evidence_pack=report_evidence_command(),
            idempotency_key="different-repository-key",
        )


def test_report_evidence_command_rejects_blank_conversion_intent_id() -> None:
    evidence_pack = report_evidence_command()
    with pytest.raises(ValueError, match="is required"):
        RequestReportEvidencePackToRepositoryCommand(
            conversion_intent_id=" ",
            evidence_pack=evidence_pack,
            idempotency_key=evidence_pack.idempotency_key,
        )


class PrecheckedReportEvidenceRepository:
    def __init__(
        self,
        repository: InMemoryIdeaRepository,
        prechecked: EvidencePackPersistenceResult,
    ) -> None:
        self._repository = repository
        self._prechecked = prechecked

    def precheck_evidence_pack_mutation(self, **kwargs: Any) -> EvidencePackPersistenceResult:
        return self._prechecked

    def conversion_intent_by_id(self, conversion_intent_id: str) -> Any:
        return self._repository.conversion_intent_by_id(conversion_intent_id)

    def candidate_record_for_conversion_intent(self, conversion_intent_id: str) -> Any:
        return self._repository.candidate_record_for_conversion_intent(conversion_intent_id)

    def record_report_evidence_pack(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("prechecked replay must not persist another evidence pack")
