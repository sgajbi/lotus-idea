from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable

from app.domain import (
    AIExplanationLineagePersistenceResult,
    AIExplanationResult,
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    ConversionIntentResult,
    ConversionOutcomeResult,
    ConversionOutcomeIdentity,
    ConversionPersistenceResult,
    EvidenceReplayResult,
    EvidencePackPersistenceResult,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    GovernedReportEvidencePack,
    DownstreamSubmissionRecord,
    IdeaCandidate,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    LifecyclePersistenceResult,
    OutboxDeliveryResult,
    OutboxEventRecord,
    OutboxDeadLetterSummary,
    OutboxRecoveryAuditRecord,
    OutboxRecoveryClaimResult,
    QueueAccessScopeFilter,
    ReportEvidencePackResult,
    ReviewActionResult,
    ReviewMutationIdentity,
    ReviewPersistenceResult,
    FeedbackResult,
    SourceRef,
)
from app.domain.idempotency import IdempotencyDecision


@dataclass(frozen=True)
class ReviewQueueRepositoryPage:
    candidate_records: tuple[CandidatePersistenceRecord, ...]
    total_reviewable_item_count: int
    total_excluded_candidate_count: int

    @property
    def has_review_queue_projection(self) -> bool:
        return True


@dataclass(frozen=True)
class ReviewQueueReadinessRepositorySummary:
    candidate_snapshot_count: int
    reviewable_item_count: int
    excluded_candidate_count: int
    exclusion_counts: Mapping[str, int]
    scored_candidate_count: int
    unscored_candidate_count: int


@dataclass(frozen=True)
class OutboxDeliveryReadinessRepositorySummary:
    pending_count: int
    leased_count: int
    failed_count: int
    published_count: int
    dead_letter_count: int
    expired_lease_count: int
    delivery_ready_count: int
    retry_deferred_count: int = 0


@dataclass(frozen=True)
class DownstreamRealizationReadinessRepositorySummary:
    conversion_intent_count: int
    conversion_outcome_count: int
    report_evidence_pack_request_count: int


@dataclass(frozen=True)
class RuntimeTrustTelemetryRepositorySummary:
    candidate_snapshot_count: int
    current_source_ref_count: int
    stale_or_unavailable_source_ref_count: int
    source_authority_counts: Mapping[str, int]
    freshness_counts: Mapping[str, int]
    supportability_counts: Mapping[str, int]
    lifecycle_counts: Mapping[str, int]
    review_decision_count: int
    feedback_event_count: int
    conversion_intent_count: int
    conversion_outcome_count: int
    report_evidence_pack_count: int
    lineage_materialized: bool
    source_batch_evidence_available: bool
    data_quality_status: str
    latest_source_generated_at_utc: datetime | None
    source_as_of_dates: tuple[str, ...]


class CandidateSnapshotRepository(Protocol):
    def snapshot(self) -> IdeaRepositorySnapshot: ...


@runtime_checkable
class CandidateDetailProjectionRepository(Protocol):
    def candidate_record_by_id(self, candidate_id: str) -> CandidatePersistenceRecord | None: ...


@runtime_checkable
class ReviewQueueProjectionRepository(Protocol):
    def review_queue_candidate_page(
        self,
        *,
        access_scope_filter: QueueAccessScopeFilter | None,
        limit: int,
        offset: int,
    ) -> ReviewQueueRepositoryPage: ...


@runtime_checkable
class ReviewQueueReadinessProjectionRepository(Protocol):
    def review_queue_readiness_summary(
        self,
        *,
        access_scope_filter: QueueAccessScopeFilter | None,
    ) -> ReviewQueueReadinessRepositorySummary: ...


@runtime_checkable
class OutboxDeliveryReadinessProjectionRepository(Protocol):
    def outbox_delivery_readiness_summary(
        self,
        *,
        max_retry_count: int,
        evaluated_at_utc: datetime,
    ) -> OutboxDeliveryReadinessRepositorySummary: ...


@runtime_checkable
class DownstreamRealizationReadinessProjectionRepository(Protocol):
    def downstream_realization_readiness_summary(
        self,
    ) -> DownstreamRealizationReadinessRepositorySummary: ...


@runtime_checkable
class RuntimeTrustTelemetryProjectionRepository(Protocol):
    def runtime_trust_telemetry_summary(self) -> RuntimeTrustTelemetryRepositorySummary: ...


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
        identity: ReviewMutationIdentity,
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

    def conversion_outcomes_for_intent(
        self,
        conversion_intent_id: str,
    ) -> tuple[GovernedConversionOutcome, ...]: ...

    def precheck_conversion_outcome_mutation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
        identity: ConversionOutcomeIdentity,
    ) -> ConversionPersistenceResult | None: ...

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

    def record_ai_explanation_lineage_request(
        self,
        result: AIExplanationResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> AIExplanationLineagePersistenceResult: ...


class DownstreamSubmissionRepository(CandidateSnapshotRepository, Protocol):
    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None: ...

    def report_evidence_pack_by_id(
        self,
        report_evidence_pack_id: str,
    ) -> GovernedReportEvidencePack | None: ...

    def downstream_submission_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DownstreamSubmissionRecord | None: ...

    def record_downstream_submission(self, record: DownstreamSubmissionRecord) -> None: ...


class OutboxDeliveryRepository(CandidateSnapshotRepository, Protocol):
    def record_outbox_delivery_run_request(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> IdempotencyDecision: ...

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
        failed_at_utc: datetime | None = None,
        max_retry_count: int = 3,
        next_attempt_at_utc: datetime | None = None,
    ) -> OutboxDeliveryResult: ...


class OutboxRecoveryRepository(OutboxDeliveryRepository, Protocol):
    def dead_letter_summaries(
        self,
        *,
        limit: int = 100,
    ) -> tuple[OutboxDeadLetterSummary, ...]: ...

    def claim_dead_letter_for_recovery(
        self,
        *,
        support_reference: str,
        idempotency_key: str,
        request_payload: Mapping[str, Any],
        actor_subject: str,
        reason: str,
        change_reference: str,
        requested_at_utc: datetime,
        lease_owner: str,
        lease_attempt_id: str,
        lease_expires_at_utc: datetime,
        max_recovery_attempts: int = 1,
    ) -> OutboxRecoveryClaimResult: ...

    def outbox_recovery_audit_records(self) -> tuple[OutboxRecoveryAuditRecord, ...]: ...


class IdeaRepository(
    CandidatePersistenceRepository,
    CandidateLifecycleRepository,
    CandidateEvidenceReplayRepository,
    ReviewWorkflowRepository,
    ConversionWorkflowRepository,
    ReportEvidenceWorkflowRepository,
    AIExplanationRepository,
    DownstreamSubmissionRepository,
    OutboxRecoveryRepository,
    Protocol,
):
    """Complete repository port surface used by API runtime wiring."""

    pass
