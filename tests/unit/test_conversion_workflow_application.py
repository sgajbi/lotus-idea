from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.conversion_workflow import (
    ConversionAccessScopeDenied,
    RequestConversionIntentToRepositoryCommand,
    request_conversion_intent_to_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    ConversionIntentCommand,
    ConversionPersistenceDecision,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    InMemoryIdeaRepository,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
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

    assert result.conversion_result is not None
    assert result.persistence.decision is ConversionPersistenceDecision.ACCEPTED
    assert repository.looked_up_candidate_ids == ["idea-conversion-workflow-001"]


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

    assert result.conversion_result is None
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
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        evidence_packet=evidence_packet,
        source_signal_ids=("signal-conversion-workflow-001",),
        score=IdeaScore(
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
