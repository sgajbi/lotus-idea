from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.persistence_summary import persistence_summary_payload
from app.api.request_validation import require_non_empty_reason_codes
from app.api.review_workflow_operations import build_review_actor_context
from app.api.temporal_validation import require_timezone_aware
from app.application.review_workflow import (
    ApplyReviewActionToRepositoryCommand,
    RecordFeedbackToRepositoryCommand,
)
from app.domain import (
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackCommand,
    EventLineageContext,
    FeedbackOutcome,
    FeedbackReason,
    CandidateEvidenceIdentity,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReasonCode,
    ReviewAction,
    ReviewActorRole,
    ReviewChannel,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
    SourceCutPosture,
    SuppressionReason,
)
from app.security.caller_context import CallerContext


class ReviewActionRequest(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    action: ReviewAction
    reason_codes: tuple[ReasonCode, ...] = Field(
        ...,
        alias="reasonCodes",
        description=(
            "Review reasons supplied by the caller. Lotus Idea records the action-owned reason "
            "for the requested review action exactly once, whether or not the caller includes it."
        ),
    )
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    review_channel: ReviewChannel = Field(..., alias="reviewChannel")
    expected_material_version: int = Field(..., alias="expectedMaterialVersion", gt=0)
    expected_evidence_version: int = Field(..., alias="expectedEvidenceVersion", gt=0)
    expected_evidence_packet_id: str = Field(..., alias="expectedEvidencePacketId")
    expected_evidence_content_hash: str = Field(..., alias="expectedEvidenceContentHash")
    expected_source_revision_vector_digest: str = Field(
        ...,
        alias="expectedSourceRevisionVectorDigest",
    )
    expected_source_cut_posture: SourceCutPosture = Field(
        ...,
        alias="expectedSourceCutPosture",
    )
    presentation_receipt_id: str | None = Field(default=None, alias="presentationReceiptId")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")

    @field_validator(
        "review_id",
        "expected_evidence_packet_id",
        "expected_evidence_content_hash",
        "expected_source_revision_vector_digest",
    )
    @classmethod
    def _review_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewId is required")
        return value

    @field_validator("decided_at_utc", "snoozed_until_utc")
    @classmethod
    def _datetime_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_timezone_aware(
            value,
            field_name="datetime",
            message="datetime fields must be timezone-aware",
        )

    _reason_codes_must_not_be_empty = field_validator("reason_codes")(
        require_non_empty_reason_codes
    )

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        role: ReviewActorRole,
        idempotency_key: str,
        accepted_at_utc: datetime,
        event_lineage: EventLineageContext,
    ) -> ApplyReviewActionToRepositoryCommand:
        return ApplyReviewActionToRepositoryCommand(
            candidate_id=candidate_id,
            review=ReviewDecisionCommand(
                review_id=self.review_id,
                action=self.action,
                actor=build_review_actor_context(caller=caller, role=role),
                reason_codes=self.reason_codes,
                decided_at_utc=self.decided_at_utc,
                expected_candidate_evidence=CandidateEvidenceIdentity(
                    candidate_id=candidate_id,
                    material_version=self.expected_material_version,
                    evidence_version=self.expected_evidence_version,
                    evidence_packet_id=self.expected_evidence_packet_id,
                    evidence_content_hash=self.expected_evidence_content_hash,
                    source_revision_vector_digest=(self.expected_source_revision_vector_digest),
                    source_cut_posture=self.expected_source_cut_posture,
                ),
                review_channel=self.review_channel,
                presentation_receipt_id=self.presentation_receipt_id,
                suppression_reason=self.suppression_reason,
                snoozed_until_utc=self.snoozed_until_utc,
            ),
            idempotency_key=idempotency_key,
            accepted_at_utc=accepted_at_utc,
            event_lineage=event_lineage,
        )


class FeedbackRequest(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    taxonomy_version: str = Field(
        ...,
        alias="taxonomyVersion",
        description=f"Governed Lotus Idea feedback taxonomy; must be {FEEDBACK_TAXONOMY_VERSION}.",
    )
    outcome: FeedbackOutcome
    reason: FeedbackReason = Field(
        ...,
        description=(
            "Governed reason for the adviser usefulness judgment. The outcome/reason "
            "combination is validated by Lotus Idea and fails closed when invalid."
        ),
    )
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @field_validator("feedback_id")
    @classmethod
    def _feedback_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("feedbackId is required")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def _recorded_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="recordedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        role: ReviewActorRole,
        idempotency_key: str,
        accepted_at_utc: datetime,
        event_lineage: EventLineageContext,
    ) -> RecordFeedbackToRepositoryCommand:
        return RecordFeedbackToRepositoryCommand(
            candidate_id=candidate_id,
            feedback=FeedbackCommand(
                feedback_id=self.feedback_id,
                actor=build_review_actor_context(caller=caller, role=role),
                outcome=self.outcome,
                reason=self.reason,
                taxonomy_version=self.taxonomy_version,
                recorded_at_utc=self.recorded_at_utc,
            ),
            idempotency_key=idempotency_key,
            accepted_at_utc=accepted_at_utc,
            event_lineage=event_lineage,
        )


class ReviewDecisionResponse(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    source_revision_vector_digest: str = Field(..., alias="sourceRevisionVectorDigest")
    source_cut_posture: SourceCutPosture = Field(..., alias="sourceCutPosture")
    candidate_material_version: int = Field(..., alias="candidateMaterialVersion")
    candidate_evidence_version: int = Field(..., alias="candidateEvidenceVersion")
    review_channel: ReviewChannel = Field(..., alias="reviewChannel")
    presentation_receipt_id: str | None = Field(default=None, alias="presentationReceiptId")
    queue_snapshot_digest: str | None = Field(default=None, alias="queueSnapshotDigest")
    review_policy_version: str = Field(..., alias="reviewPolicyVersion")
    authority_policy_version: str = Field(..., alias="authorityPolicyVersion")
    action: ReviewAction
    resulting_posture: str = Field(..., alias="resultingPosture")
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    accepted_at_utc: datetime = Field(..., alias="acceptedAtUtc")
    acceptance_time_source: str = Field(..., alias="acceptanceTimeSource")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, decision: GovernedReviewDecision) -> "ReviewDecisionResponse":
        return cls(
            reviewId=decision.review_id,
            candidateId=decision.candidate_id,
            evidencePacketId=decision.evidence_packet_id,
            evidenceContentHash=decision.evidence_content_hash,
            sourceRevisionVectorDigest=decision.source_revision_vector_digest,
            sourceCutPosture=decision.source_cut_posture,
            candidateMaterialVersion=decision.candidate_material_version,
            candidateEvidenceVersion=decision.candidate_evidence_version,
            reviewChannel=decision.review_channel,
            presentationReceiptId=decision.presentation_receipt_id,
            queueSnapshotDigest=decision.queue_snapshot_digest,
            reviewPolicyVersion=decision.review_policy_version,
            authorityPolicyVersion=decision.review_authority_policy_version,
            action=decision.action,
            resultingPosture=decision.resulting_posture.value,
            actorRole=decision.actor_role,
            reasonCodes=tuple(reason.value for reason in decision.reason_codes),
            decidedAtUtc=decision.decided_at_utc,
            acceptedAtUtc=decision.accepted_at_utc,
            acceptanceTimeSource=decision.acceptance_time_source.value,
            suppressionReason=decision.suppression_reason,
            snoozedUntilUtc=decision.snoozed_until_utc,
            grantsDownstreamAuthority=decision.grants_downstream_authority,
        )


class FeedbackEventResponse(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    taxonomy_version: str = Field(..., alias="taxonomyVersion")
    outcome: FeedbackOutcome
    reason: FeedbackReason
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")
    accepted_at_utc: datetime = Field(..., alias="acceptedAtUtc")
    acceptance_time_source: str = Field(..., alias="acceptanceTimeSource")

    @classmethod
    def from_domain(cls, event: GovernedFeedbackEvent) -> "FeedbackEventResponse":
        return cls(
            feedbackId=event.feedback.feedback_id,
            candidateId=event.candidate_id,
            evidencePacketId=event.evidence_packet_id,
            taxonomyVersion=event.feedback.taxonomy_version,
            outcome=event.feedback.outcome,
            reason=event.feedback.reason,
            actorRole=event.actor_role,
            recordedAtUtc=event.feedback.recorded_at_utc,
            acceptedAtUtc=event.accepted_at_utc,
            acceptanceTimeSource=event.acceptance_time_source.value,
        )


class ReviewPersistenceSummaryResponse(CamelModel):
    decision: ReviewPersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    review_posture: str | None = Field(default=None, alias="reviewPosture")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: ReviewPersistenceResult,
    ) -> "ReviewPersistenceSummaryResponse":
        return cls(**persistence_summary_payload(result))


class ReviewActionResponse(CamelModel):
    review_decision: ReviewDecisionResponse = Field(..., alias="reviewDecision")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class FeedbackResponse(CamelModel):
    feedback_event: FeedbackEventResponse = Field(..., alias="feedbackEvent")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


__all__ = [
    "FeedbackEventResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "ReviewActionRequest",
    "ReviewActionResponse",
    "ReviewDecisionResponse",
    "ReviewPersistenceSummaryResponse",
]
