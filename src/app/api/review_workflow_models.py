from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.api.access_scope_models import ReviewAccessScopeRequest
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
    FeedbackCommand,
    FeedbackOutcome,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReasonCode,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
    SuppressionReason,
)
from app.security.caller_context import CallerContext, CallerEntitlementScope


class ReviewActorScopeRequest(CamelModel):
    tenant_ids: tuple[str, ...] = Field(..., alias="tenantIds")
    book_ids: tuple[str, ...] = Field(..., alias="bookIds")
    portfolio_ids: tuple[str, ...] = Field(..., alias="portfolioIds")
    client_ids: tuple[str, ...] = Field(..., alias="clientIds")

    @field_validator("tenant_ids", "book_ids", "portfolio_ids", "client_ids")
    @classmethod
    def _scope_set_must_not_be_empty_or_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("authorized scope fields cannot be empty")
        if any(not item.strip() for item in value):
            raise ValueError("authorized scope fields cannot contain blank values")
        return tuple(value)

    def to_actor_context(
        self,
        *,
        caller: CallerContext,
        role: ReviewActorRole,
    ) -> ReviewActorContext:
        return ReviewActorContext(
            actor_subject=caller.subject,
            role=role,
            tenant_ids=frozenset(self.tenant_ids),
            book_ids=frozenset(self.book_ids),
            portfolio_ids=frozenset(self.portfolio_ids),
            client_ids=frozenset(self.client_ids),
        )

    def is_subset_of_entitlement_scope(self, scope: CallerEntitlementScope) -> bool:
        return (
            _values_are_subset(self.tenant_ids, scope.tenant_ids)
            and _values_are_subset(self.book_ids, scope.book_ids)
            and _values_are_subset(self.portfolio_ids, scope.portfolio_ids)
            and _values_are_subset(self.client_ids, scope.client_ids)
        )


class ReviewActionRequest(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    action: ReviewAction
    access_scope: ReviewAccessScopeRequest = Field(..., alias="accessScope")
    authorized_scope: ReviewActorScopeRequest = Field(..., alias="authorizedScope")
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")

    @field_validator("review_id")
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
    ) -> ApplyReviewActionToRepositoryCommand:
        return ApplyReviewActionToRepositoryCommand(
            candidate_id=candidate_id,
            review=ReviewDecisionCommand(
                review_id=self.review_id,
                action=self.action,
                actor=build_review_actor_context(caller=caller, role=role),
                access_scope=self.access_scope.to_domain(),
                reason_codes=self.reason_codes,
                decided_at_utc=self.decided_at_utc,
                suppression_reason=self.suppression_reason,
                snoozed_until_utc=self.snoozed_until_utc,
            ),
            idempotency_key=idempotency_key,
        )


class FeedbackRequest(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    access_scope: ReviewAccessScopeRequest = Field(..., alias="accessScope")
    authorized_scope: ReviewActorScopeRequest = Field(..., alias="authorizedScope")
    outcome: FeedbackOutcome
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
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
    ) -> RecordFeedbackToRepositoryCommand:
        return RecordFeedbackToRepositoryCommand(
            candidate_id=candidate_id,
            feedback=FeedbackCommand(
                feedback_id=self.feedback_id,
                actor=build_review_actor_context(caller=caller, role=role),
                access_scope=self.access_scope.to_domain(),
                outcome=self.outcome,
                reason_codes=self.reason_codes,
                recorded_at_utc=self.recorded_at_utc,
            ),
            idempotency_key=idempotency_key,
        )


class ReviewDecisionResponse(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    action: ReviewAction
    resulting_posture: str = Field(..., alias="resultingPosture")
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, decision: GovernedReviewDecision) -> "ReviewDecisionResponse":
        return cls(
            reviewId=decision.review_id,
            candidateId=decision.candidate_id,
            evidencePacketId=decision.evidence_packet_id,
            action=decision.action,
            resultingPosture=decision.resulting_posture.value,
            actorRole=decision.actor_role,
            reasonCodes=tuple(reason.value for reason in decision.reason_codes),
            decidedAtUtc=decision.decided_at_utc,
            suppressionReason=decision.suppression_reason,
            snoozedUntilUtc=decision.snoozed_until_utc,
            grantsDownstreamAuthority=decision.grants_downstream_authority,
        )


class FeedbackEventResponse(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    outcome: FeedbackOutcome
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @classmethod
    def from_domain(cls, event: GovernedFeedbackEvent) -> "FeedbackEventResponse":
        return cls(
            feedbackId=event.feedback.feedback_id,
            candidateId=event.candidate_id,
            evidencePacketId=event.evidence_packet_id,
            outcome=event.feedback.outcome,
            actorRole=event.actor_role,
            reasonCodes=tuple(reason.value for reason in event.feedback.reason_codes),
            recordedAtUtc=event.feedback.recorded_at_utc,
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
    review_decision: ReviewDecisionResponse | None = Field(default=None, alias="reviewDecision")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class FeedbackResponse(CamelModel):
    feedback_event: FeedbackEventResponse | None = Field(default=None, alias="feedbackEvent")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


def _values_are_subset(values: tuple[str, ...], allowed_values: tuple[str, ...]) -> bool:
    return bool(allowed_values) and set(values).issubset(allowed_values)


__all__ = [
    "FeedbackEventResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "ReviewActionRequest",
    "ReviewActionResponse",
    "ReviewActorScopeRequest",
    "ReviewDecisionResponse",
    "ReviewPersistenceSummaryResponse",
]
