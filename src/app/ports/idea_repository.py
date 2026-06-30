from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.domain import (
    AIExplanationLineagePersistenceResult,
    AIExplanationResult,
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    ConversionIntentResult,
    ConversionOutcomeResult,
    ConversionPersistenceResult,
    EvidenceReplayResult,
    EvidencePackPersistenceResult,
    GovernedConversionIntent,
    DownstreamSubmissionRecord,
    IdeaCandidate,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    LifecyclePersistenceResult,
    OutboxDeliveryResult,
    OutboxEventRecord,
    ReportEvidencePackResult,
    ReviewActionResult,
    ReviewPersistenceResult,
    FeedbackResult,
    SourceRef,
)


class CandidateSnapshotRepository(Protocol):
    def snapshot(self) -> IdeaRepositorySnapshot: ...


class CandidatePersistenceRepository(Protocol):
    def persist_candidate(
        self,
        candidate: IdeaCandidate,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
    ) -> CandidatePersistenceResult: ...


class CandidateLifecycleRepository(Protocol):
    def record_lifecycle_transition(
        self,
        candidate_id: str,
        target_status: IdeaLifecycleStatus,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
        transition_id: str | None = None,
        reason_codes: tuple[str, ...] = (),
    ) -> LifecyclePersistenceResult: ...


class CandidateEvidenceReplayRepository(Protocol):
    def replay_evidence(
        self,
        candidate_id: str,
        *,
        current_source_refs: tuple[SourceRef, ...],
        evaluated_at_utc: datetime | None = None,
    ) -> EvidenceReplayResult: ...


class ReviewWorkflowRepository(CandidateSnapshotRepository, Protocol):
    def precheck_review_mutation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult | None: ...

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult: ...

    def record_feedback_event(
        self,
        result: FeedbackResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ReviewPersistenceResult: ...


class ConversionWorkflowRepository(CandidateSnapshotRepository, Protocol):
    def precheck_conversion_mutation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ConversionPersistenceResult | None: ...

    def record_conversion_intent(
        self,
        result: ConversionIntentResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ConversionPersistenceResult: ...

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None: ...

    def record_conversion_outcome(
        self,
        result: ConversionOutcomeResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ConversionPersistenceResult: ...


class ReportEvidenceWorkflowRepository(Protocol):
    def precheck_evidence_pack_mutation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> EvidencePackPersistenceResult | None: ...

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None: ...

    def candidate_record_for_conversion_intent(
        self,
        conversion_intent_id: str,
    ) -> CandidatePersistenceRecord | None: ...

    def record_report_evidence_pack(
        self,
        result: ReportEvidencePackResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> EvidencePackPersistenceResult: ...


class AIExplanationRepository(CandidateSnapshotRepository, Protocol):
    def record_ai_explanation_lineage(
        self,
        result: AIExplanationResult,
    ) -> AIExplanationLineagePersistenceResult: ...


class DownstreamSubmissionRepository(CandidateSnapshotRepository, Protocol):
    def downstream_submission_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DownstreamSubmissionRecord | None: ...

    def record_downstream_submission(self, record: DownstreamSubmissionRecord) -> None: ...


class OutboxDeliveryRepository(CandidateSnapshotRepository, Protocol):
    def outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        evaluated_at_utc: datetime | None = None,
    ) -> tuple[OutboxEventRecord, ...]: ...

    def claim_outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        lease_owner: str,
        lease_attempt_id: str,
        claimed_at_utc: datetime,
        lease_expires_at_utc: datetime,
    ) -> tuple[OutboxEventRecord, ...]: ...

    def mark_outbox_event_published(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        published_at_utc: datetime,
    ) -> OutboxDeliveryResult: ...

    def mark_outbox_event_failed(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        failure_reason: str,
        max_retry_count: int = 3,
    ) -> OutboxDeliveryResult: ...


class IdeaRepository(
    CandidatePersistenceRepository,
    CandidateLifecycleRepository,
    CandidateEvidenceReplayRepository,
    ReviewWorkflowRepository,
    ConversionWorkflowRepository,
    ReportEvidenceWorkflowRepository,
    AIExplanationRepository,
    DownstreamSubmissionRepository,
    OutboxDeliveryRepository,
    Protocol,
):
    """Complete repository port surface used by API runtime wiring."""

    pass
