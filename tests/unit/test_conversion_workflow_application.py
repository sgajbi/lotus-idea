from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from functools import partial
from typing import Any

import pytest

from tests.support.candidate_identity import initial_candidate_identity
from tests.support.score_fixture import score_fixture

from app.application.conversion_workflow import (
    ConversionAccessScopeDenied,
    ConversionIntentWorkflowResult,
    RequestConversionIntentToRepositoryCommand as _RequestConversionIntentToRepositoryCommand,
    request_conversion_intent_to_repository,
)
from app.application.persisted_action_evidence import PersistedActionEvidenceUnavailable
from app.domain import (
    CandidatePersistenceDecision,
    ConversionIntentCommand,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    InMemoryIdeaRepository,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    SourceSystem,
)
from app.domain.access_scope import QueueAccessScopeFilter, ReviewAccessScope

AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)

RequestConversionIntentToRepositoryCommand = partial(
    _RequestConversionIntentToRepositoryCommand,
    accepted_at_utc=REQUESTED_AT,
)


def test_request_conversion_intent_uses_candidate_projection_without_snapshot() -> None:
    repository = ProjectionOnlyConversionWorkflowRepository(repository_with_approved_candidate())

    result = request_conversion_intent_to_repository(
        RequestConversionIntentToRepositoryCommand(
            candidate_id="idea-conversion-workflow-001",
            conversion=conversion_command(),
            idempotency_key="conversion-workflow-request-001",
            access_scope_filter=authorized_scope_filter(),
        ),
        repository=repository,
    )

    assert result.conversion_intent is not None
    assert result.persistence.decision is ConversionPersistenceDecision.ACCEPTED
    assert repository.looked_up_candidate_ids == ["idea-conversion-workflow-001"]


def test_conversion_intent_replay_returns_exact_persisted_intent() -> None:
    repository = repository_with_approved_candidate()
    command = RequestConversionIntentToRepositoryCommand(
        candidate_id="idea-conversion-workflow-001",
        conversion=conversion_command(),
        idempotency_key="conversion-workflow-request-001",
        access_scope_filter=authorized_scope_filter(),
    )

    accepted = request_conversion_intent_to_repository(command, repository=repository)
    replayed = request_conversion_intent_to_repository(command, repository=repository)

    assert accepted.conversion_intent is not None
    assert replayed.conversion_intent == accepted.conversion_intent
    assert replayed.persistence.decision is ConversionPersistenceDecision.REPLAYED
    assert replayed.persistence.record == accepted.persistence.record
    assert replayed.persistence.record is not None
    assert len(replayed.persistence.record.conversion_intents) == 1


def test_conversion_intent_replay_retains_original_server_acceptance_time() -> None:
    repository = repository_with_approved_candidate()
    first_accepted_at = REQUESTED_AT + datetime.resolution
    command = RequestConversionIntentToRepositoryCommand(
        candidate_id="idea-conversion-workflow-001",
        conversion=conversion_command(),
        idempotency_key="conversion-workflow-request-001",
        accepted_at_utc=first_accepted_at,
        access_scope_filter=authorized_scope_filter(),
    )

    accepted = request_conversion_intent_to_repository(command, repository=repository)
    replayed = request_conversion_intent_to_repository(
        _RequestConversionIntentToRepositoryCommand(
            candidate_id=command.candidate_id,
            conversion=command.conversion,
            idempotency_key=command.idempotency_key,
            accepted_at_utc=first_accepted_at + datetime.resolution,
            access_scope_filter=command.access_scope_filter,
        ),
        repository=repository,
    )

    assert accepted.require_conversion_intent().accepted_at_utc == first_accepted_at
    assert replayed.require_conversion_intent().accepted_at_utc == first_accepted_at
    assert replayed.persistence.decision is ConversionPersistenceDecision.REPLAYED


def test_conversion_intent_replay_fails_closed_when_persisted_intent_is_missing() -> None:
    repository = repository_with_approved_candidate()
    record = repository.candidate_record_by_id("idea-conversion-workflow-001")
    assert record is not None
    replay_repository = PrecheckedConversionWorkflowRepository(
        repository,
        ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.REPLAYED,
            record=record,
        ),
    )

    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="exactly one persisted action",
    ):
        request_conversion_intent_to_repository(
            RequestConversionIntentToRepositoryCommand(
                candidate_id="idea-conversion-workflow-001",
                conversion=conversion_command(),
                idempotency_key="conversion-workflow-request-001",
                access_scope_filter=authorized_scope_filter(),
            ),
            repository=replay_repository,
        )


def test_success_result_guard_rejects_missing_conversion_intent_evidence() -> None:
    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="no persisted conversion intent",
    ):
        ConversionIntentWorkflowResult(
            conversion_intent=None,
            persistence=ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.REPLAYED,
                record=None,
            ),
        ).require_conversion_intent()


def test_successful_conversion_replay_requires_matching_candidate_record() -> None:
    repository = repository_with_approved_candidate()
    replay_repository = PrecheckedConversionWorkflowRepository(
        repository,
        ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.REPLAYED,
            record=None,
        ),
    )

    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="conversion mutation has no matching candidate record",
    ):
        request_conversion_intent_to_repository(
            RequestConversionIntentToRepositoryCommand(
                candidate_id="idea-conversion-workflow-001",
                conversion=conversion_command(),
                idempotency_key="conversion-workflow-request-001",
                access_scope_filter=authorized_scope_filter(),
            ),
            repository=replay_repository,
        )


def test_request_conversion_intent_returns_not_found_without_snapshot_for_missing_candidate() -> (
    None
):
    repository = ProjectionOnlyConversionWorkflowRepository(InMemoryIdeaRepository())

    result = request_conversion_intent_to_repository(
        RequestConversionIntentToRepositoryCommand(
            candidate_id="missing-candidate",
            conversion=conversion_command(),
            idempotency_key="conversion-workflow-request-001",
            access_scope_filter=authorized_scope_filter(),
        ),
        repository=repository,
    )

    assert result.conversion_intent is None
    assert result.persistence.decision is ConversionPersistenceDecision.NOT_FOUND
    assert result.persistence.record is None
    assert repository.looked_up_candidate_ids == ["missing-candidate"]


def test_request_conversion_intent_rejects_mismatched_idempotency_boundary() -> None:
    with pytest.raises(
        ValueError,
        match="conversion idempotency key must match repository idempotency key",
    ):
        RequestConversionIntentToRepositoryCommand(
            candidate_id="idea-conversion-workflow-001",
            conversion=conversion_command(),
            idempotency_key="conversion-workflow:mismatched-repository-key",
        )


def test_request_conversion_intent_rejects_missing_or_mismatched_access_scope() -> None:
    repository = ProjectionOnlyConversionWorkflowRepository(repository_with_approved_candidate())

    with pytest.raises(ConversionAccessScopeDenied):
        request_conversion_intent_to_repository(
            RequestConversionIntentToRepositoryCommand(
                candidate_id="idea-conversion-workflow-001",
                conversion=conversion_command(
                    idempotency_key="conversion-workflow-request-missing-scope-001"
                ),
                idempotency_key="conversion-workflow-request-missing-scope-001",
            ),
            repository=repository,
        )

    with pytest.raises(ConversionAccessScopeDenied):
        request_conversion_intent_to_repository(
            RequestConversionIntentToRepositoryCommand(
                candidate_id="idea-conversion-workflow-001",
                conversion=conversion_command(
                    conversion_intent_id="conversion-mismatched-scope-001",
                    idempotency_key="conversion-workflow-request-mismatched-scope-001",
                ),
                idempotency_key="conversion-workflow-request-mismatched-scope-001",
                access_scope_filter=QueueAccessScopeFilter(
                    tenant_id="tenant-private-bank-sg",
                    book_id="book-advisor-001",
                    portfolio_id="PB_SG_DIFFERENT_999",
                    client_id="client-001",
                ),
            ),
            repository=repository,
        )


def authorized_scope_filter() -> QueueAccessScopeFilter:
    return QueueAccessScopeFilter(
        tenant_id="tenant-private-bank-sg",
        book_id="book-advisor-001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )


def repository_with_approved_candidate() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        approved_candidate(),
        idempotency_key="signal-ingestion:conversion-workflow:001",
        payload={"candidate_id": "idea-conversion-workflow-001"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
    return repository


def approved_candidate() -> IdeaCandidate:
    source = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id="iep_conversion_workflow_test",
        supportability=EvidenceSupportability.READY,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id="lineage:lotus-idea:conversion-workflow:test",
            source_refs=(source,),
            content_hash="sha256:conversion-workflow-lineage",
        ),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=EVALUATED_AT,
    )
    return IdeaCandidate(
        candidate_id="idea-conversion-workflow-001",
        identity=initial_candidate_identity("idea-conversion-workflow-001"),
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        evidence_packet=evidence_packet,
        source_signal_ids=("signal-conversion-workflow-001",),
        score=score_fixture(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("88"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
        access_scope=ReviewAccessScope(
            tenant_id="tenant-private-bank-sg",
            book_id="book-advisor-001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            client_id="client-001",
        ),
    )


def conversion_command(
    *,
    conversion_intent_id: str = "conversion-workflow-report-001",
    idempotency_key: str = "conversion-workflow-request-001",
) -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id=conversion_intent_id,
        target=ConversionTarget.REPORT_EVIDENCE,
        actor_subject="advisor-001",
        idempotency_key=idempotency_key,
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=REQUESTED_AT,
    )


class ProjectionOnlyConversionWorkflowRepository:
    def __init__(self, repository: InMemoryIdeaRepository) -> None:
        self._repository = repository
        self.looked_up_candidate_ids: list[str] = []

    def candidate_record_by_id(self, candidate_id: str) -> Any:
        self.looked_up_candidate_ids.append(candidate_id)
        return self._repository.candidate_record_by_id(candidate_id)

    def precheck_conversion_mutation(self, **kwargs: Any) -> Any:
        return self._repository.precheck_conversion_mutation(**kwargs)

    def record_conversion_intent(self, *args: Any, **kwargs: Any) -> Any:
        return self._repository.record_conversion_intent(*args, **kwargs)

    def conversion_intent_by_id(self, conversion_intent_id: str) -> Any:
        return self._repository.conversion_intent_by_id(conversion_intent_id)

    def record_conversion_outcome(self, *args: Any, **kwargs: Any) -> Any:
        return self._repository.record_conversion_outcome(*args, **kwargs)

    def snapshot(self) -> Any:
        raise AssertionError(
            "conversion workflow candidate lookup must not hydrate a full snapshot"
        )


class PrecheckedConversionWorkflowRepository(ProjectionOnlyConversionWorkflowRepository):
    def __init__(
        self,
        repository: InMemoryIdeaRepository,
        prechecked: ConversionPersistenceResult,
    ) -> None:
        super().__init__(repository)
        self._prechecked = prechecked

    def precheck_conversion_mutation(self, **kwargs: Any) -> ConversionPersistenceResult:
        return self._prechecked
