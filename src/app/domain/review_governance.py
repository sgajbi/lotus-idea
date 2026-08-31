from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.access_scope import ReviewAccessScope
from app.domain.audit import AuditEvent
from app.domain.candidate_state import (
    CANDIDATE_STATE_POLICY_VERSION,
    REVIEWABLE_LIFECYCLE_STATUSES,
)
from app.domain.feedback_taxonomy import (
    FeedbackOutcome,
    FeedbackReason,
    validate_feedback_taxonomy,
)
from app.domain.ideas import (
    EvidenceSupportability,
    IdeaCandidate,
    IdeaFeedback,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SuppressionReason,
    transition_candidate,
)
from app.domain.review_queue import (
    DEFAULT_REVIEW_QUEUE_POLICY,
    QueuePriorityBucket,
    QueueSnooze,
    priority_bucket_for_score,
)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class ReviewActorRole(StrEnum):
    ADVISOR = "advisor"
    PORTFOLIO_MANAGER = "portfolio_manager"
    COMPLIANCE = "compliance"
    OPERATOR = "operator"


class ReviewAction(StrEnum):
    APPROVE_FOR_CONVERSION = "approve_for_conversion"
    REJECT = "reject"
    NO_ACTION = "no_action"
    SUPPRESS = "suppress"
    SNOOZE = "snooze"
    ESCALATE_TO_PM = "escalate_to_pm"
    ESCALATE_TO_COMPLIANCE = "escalate_to_compliance"


class ReviewMutationType(StrEnum):
    REVIEW_DECISION = "review_decision"
    FEEDBACK_EVENT = "feedback_event"


class ReviewEntitlementDenied(PermissionError):
    def __init__(self, candidate_id: str) -> None:
        super().__init__("Review action is not permitted for this caller and candidate scope")
        self.candidate_id = candidate_id


class InvalidReviewAction(ValueError):
    code = "review_action_conflict"

    def __init__(
        self,
        action: ReviewAction,
        lifecycle_status: IdeaLifecycleStatus,
        review_posture: ReviewPosture,
    ) -> None:
        super().__init__(
            "Invalid review action for candidate state under "
            f"{CANDIDATE_STATE_POLICY_VERSION}: "
            f"{action.value} -> {lifecycle_status.value}/{review_posture.value}"
        )
        self.action = action
        self.lifecycle_status = lifecycle_status
        self.review_posture = review_posture
        self.policy_version = CANDIDATE_STATE_POLICY_VERSION


@dataclass(frozen=True)
class ReviewMutationIdentity:
    mutation_type: ReviewMutationType
    resource_id: str
    candidate_id: str
    evidence_packet_id: str
    evidence_content_hash: str
    actor_subject: str
    actor_role: ReviewActorRole
    event_name: str
    reason_codes: tuple[ReasonCode, ...]
    occurred_at_utc: datetime
    resulting_posture: ReviewPosture | None = None
    suppression_reason: SuppressionReason | None = None
    snoozed_until_utc: datetime | None = None
    source_signal_ids: tuple[str, ...] = ()
    feedback_taxonomy_version: str | None = None
    feedback_reason: FeedbackReason | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "resource_id",
            "candidate_id",
            "evidence_packet_id",
            "evidence_content_hash",
            "actor_subject",
            "event_name",
        ):
            _require_text(getattr(self, field_name), field_name)
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.snoozed_until_utc is not None:
            _require_aware_utc(self.snoozed_until_utc, "snoozed_until_utc")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "source_signal_ids", tuple(self.source_signal_ids))
        feedback_fields = (self.feedback_taxonomy_version, self.feedback_reason)
        if self.mutation_type is ReviewMutationType.FEEDBACK_EVENT:
            if any(value is None for value in feedback_fields):
                raise ValueError("feedback mutation identity requires taxonomy version and reason")
        elif any(value is not None for value in feedback_fields):
            raise ValueError("review decision identity cannot carry feedback taxonomy fields")


@dataclass(frozen=True)
class ReviewActorContext:
    actor_subject: str
    role: ReviewActorRole
    tenant_ids: frozenset[str]
    book_ids: frozenset[str]
    portfolio_ids: frozenset[str]
    client_ids: frozenset[str]

    def __post_init__(self) -> None:
        _require_text(self.actor_subject, "actor_subject")
        for field_name, values in (
            ("tenant_ids", self.tenant_ids),
            ("book_ids", self.book_ids),
            ("portfolio_ids", self.portfolio_ids),
            ("client_ids", self.client_ids),
        ):
            if not values:
                raise ValueError(f"{field_name} is required")
            if any(not value.strip() for value in values):
                raise ValueError(f"{field_name} cannot contain blank values")
            object.__setattr__(self, field_name, frozenset(values))

    def can_access(self, scope: ReviewAccessScope) -> bool:
        return (
            scope.tenant_id in self.tenant_ids
            and scope.book_id in self.book_ids
            and scope.portfolio_id in self.portfolio_ids
            and scope.client_id in self.client_ids
        )


@dataclass(frozen=True)
class ReviewActionPolicy:
    policy_version: str = "idea-human-review-v1"
    allowed_roles_by_action: dict[ReviewAction, frozenset[ReviewActorRole]] | None = None

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        roles_by_action = (
            _default_allowed_roles_by_action()
            if self.allowed_roles_by_action is None
            else self.allowed_roles_by_action
        )
        for action in ReviewAction:
            if action not in roles_by_action:
                raise ValueError(f"allowed roles missing for action: {action.value}")
            if not roles_by_action[action]:
                raise ValueError(f"allowed roles required for action: {action.value}")
        object.__setattr__(
            self,
            "allowed_roles_by_action",
            {action: frozenset(roles) for action, roles in roles_by_action.items()},
        )

    def allows(self, actor: ReviewActorContext, action: ReviewAction) -> bool:
        assert self.allowed_roles_by_action is not None
        return actor.role in self.allowed_roles_by_action[action]


@dataclass(frozen=True)
class ReviewDecisionCommand:
    review_id: str
    action: ReviewAction
    actor: ReviewActorContext
    reason_codes: tuple[ReasonCode, ...]
    decided_at_utc: datetime
    suppression_reason: SuppressionReason | None = None
    snoozed_until_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.review_id, "review_id")
        _require_aware_utc(self.decided_at_utc, "decided_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.action is ReviewAction.SUPPRESS and self.suppression_reason is None:
            raise ValueError("suppression_reason is required for suppress action")
        if self.action is ReviewAction.SNOOZE:
            if self.snoozed_until_utc is None:
                raise ValueError("snoozed_until_utc is required for snooze action")
            _require_aware_utc(self.snoozed_until_utc, "snoozed_until_utc")
            if self.snoozed_until_utc <= self.decided_at_utc:
                raise ValueError("snoozed_until_utc must be after decided_at_utc")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class GovernedReviewDecision:
    review_id: str
    candidate_id: str
    evidence_packet_id: str
    evidence_content_hash: str
    action: ReviewAction
    resulting_posture: ReviewPosture
    actor_subject: str
    actor_role: ReviewActorRole
    reason_codes: tuple[ReasonCode, ...]
    decided_at_utc: datetime
    suppression_reason: SuppressionReason | None = None
    snoozed_until_utc: datetime | None = None

    @property
    def grants_downstream_authority(self) -> bool:
        return False

    @property
    def mutation_identity(self) -> ReviewMutationIdentity:
        return review_mutation_identity_from_decision(self)

    def __post_init__(self) -> None:
        _require_text(self.review_id, "review_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_text(self.evidence_content_hash, "evidence_content_hash")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.decided_at_utc, "decided_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.snoozed_until_utc is not None:
            _require_aware_utc(self.snoozed_until_utc, "snoozed_until_utc")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ReviewActionResult:
    source_candidate: IdeaCandidate
    candidate: IdeaCandidate
    decision: GovernedReviewDecision
    audit_event: AuditEvent
    queue_snooze: QueueSnooze | None = None


@dataclass(frozen=True)
class FeedbackCommand:
    feedback_id: str
    actor: ReviewActorContext
    outcome: FeedbackOutcome
    reason: FeedbackReason
    taxonomy_version: str
    recorded_at_utc: datetime

    def __post_init__(self) -> None:
        _require_text(self.feedback_id, "feedback_id")
        _require_text(self.taxonomy_version, "taxonomy_version")
        _require_aware_utc(self.recorded_at_utc, "recorded_at_utc")
        validate_feedback_taxonomy(
            taxonomy_version=self.taxonomy_version,
            outcome=self.outcome,
            reason=self.reason,
        )


@dataclass(frozen=True)
class GovernedFeedbackEvent:
    feedback: IdeaFeedback
    candidate_id: str
    evidence_packet_id: str
    evidence_content_hash: str
    source_signal_ids: tuple[str, ...]
    actor_subject: str
    actor_role: ReviewActorRole
    candidate_family: OpportunityFamily
    candidate_identity_policy_version: str
    score_policy_version: str | None
    score: Decimal | None
    evidence_supportability: EvidenceSupportability
    ranking_policy_version: str
    queue_priority_bucket: QueuePriorityBucket | None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_text(self.evidence_content_hash, "evidence_content_hash")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(
            self.candidate_identity_policy_version,
            "candidate_identity_policy_version",
        )
        _require_text(self.ranking_policy_version, "ranking_policy_version")
        if self.score_policy_version is not None:
            _require_text(self.score_policy_version, "score_policy_version")
        if (self.score is None) != (self.score_policy_version is None):
            raise ValueError("score and score_policy_version must be provided together")
        if not self.source_signal_ids:
            raise ValueError("source_signal_ids is required")
        object.__setattr__(self, "source_signal_ids", tuple(self.source_signal_ids))

    @property
    def mutation_identity(self) -> ReviewMutationIdentity:
        return feedback_mutation_identity_from_event(self)


@dataclass(frozen=True)
class FeedbackResult:
    feedback_event: GovernedFeedbackEvent
    audit_event: AuditEvent


def _default_allowed_roles_by_action() -> dict[ReviewAction, frozenset[ReviewActorRole]]:
    advisor = frozenset({ReviewActorRole.ADVISOR})
    return {
        ReviewAction.APPROVE_FOR_CONVERSION: advisor,
        ReviewAction.REJECT: advisor,
        ReviewAction.NO_ACTION: advisor,
        ReviewAction.SUPPRESS: advisor,
        ReviewAction.SNOOZE: advisor,
        ReviewAction.ESCALATE_TO_PM: advisor,
        ReviewAction.ESCALATE_TO_COMPLIANCE: advisor,
    }


DEFAULT_REVIEW_ACTION_POLICY = ReviewActionPolicy()

_REVIEW_ACTION_REASON_CODES: dict[ReviewAction, ReasonCode] = {
    ReviewAction.APPROVE_FOR_CONVERSION: ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,
    ReviewAction.REJECT: ReasonCode.REVIEW_REJECTED,
    ReviewAction.NO_ACTION: ReasonCode.REVIEW_NO_ACTION,
    ReviewAction.SUPPRESS: ReasonCode.REVIEW_SUPPRESSED,
    ReviewAction.SNOOZE: ReasonCode.REVIEW_SNOOZED,
    ReviewAction.ESCALATE_TO_PM: ReasonCode.REVIEW_ESCALATED,
    ReviewAction.ESCALATE_TO_COMPLIANCE: ReasonCode.REVIEW_ESCALATED,
}

_REVIEW_ACTION_POSTURES: dict[ReviewAction, ReviewPosture] = {
    ReviewAction.APPROVE_FOR_CONVERSION: ReviewPosture.APPROVED_FOR_CONVERSION,
    ReviewAction.REJECT: ReviewPosture.REJECTED,
    ReviewAction.NO_ACTION: ReviewPosture.NO_ACTION,
    ReviewAction.SUPPRESS: ReviewPosture.SUPPRESSED,
    ReviewAction.SNOOZE: ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    ReviewAction.ESCALATE_TO_PM: ReviewPosture.PM_REVIEW_REQUIRED,
    ReviewAction.ESCALATE_TO_COMPLIANCE: ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
}

_DECISION_LIFECYCLE_STATUSES = frozenset(
    {
        IdeaLifecycleStatus.READY_FOR_REVIEW,
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
    }
)
_REVIEW_ACTION_LIFECYCLE_STATUSES: dict[ReviewAction, frozenset[IdeaLifecycleStatus]] = {
    ReviewAction.APPROVE_FOR_CONVERSION: _DECISION_LIFECYCLE_STATUSES,
    ReviewAction.REJECT: _DECISION_LIFECYCLE_STATUSES,
    ReviewAction.NO_ACTION: _DECISION_LIFECYCLE_STATUSES,
    ReviewAction.SUPPRESS: REVIEWABLE_LIFECYCLE_STATUSES
    | {IdeaLifecycleStatus.REVIEWED_BY_ADVISOR},
    ReviewAction.SNOOZE: REVIEWABLE_LIFECYCLE_STATUSES | {IdeaLifecycleStatus.REVIEWED_BY_ADVISOR},
    ReviewAction.ESCALATE_TO_PM: REVIEWABLE_LIFECYCLE_STATUSES
    | {IdeaLifecycleStatus.REVIEWED_BY_ADVISOR},
    ReviewAction.ESCALATE_TO_COMPLIANCE: REVIEWABLE_LIFECYCLE_STATUSES
    | {IdeaLifecycleStatus.REVIEWED_BY_ADVISOR},
}


def review_mutation_identity_from_command(
    candidate: IdeaCandidate,
    command: ReviewDecisionCommand,
) -> ReviewMutationIdentity:
    return ReviewMutationIdentity(
        mutation_type=ReviewMutationType.REVIEW_DECISION,
        resource_id=command.review_id,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        actor_subject=command.actor.actor_subject,
        actor_role=command.actor.role,
        event_name=command.action.value,
        resulting_posture=_REVIEW_ACTION_POSTURES[command.action],
        reason_codes=_canonical_owned_reason_codes(
            owner_reason=_REVIEW_ACTION_REASON_CODES[command.action],
            caller_reason_codes=command.reason_codes,
        ),
        occurred_at_utc=command.decided_at_utc,
        suppression_reason=command.suppression_reason,
        snoozed_until_utc=command.snoozed_until_utc,
    )


def review_mutation_identity_from_decision(
    decision: GovernedReviewDecision,
) -> ReviewMutationIdentity:
    return ReviewMutationIdentity(
        mutation_type=ReviewMutationType.REVIEW_DECISION,
        resource_id=decision.review_id,
        candidate_id=decision.candidate_id,
        evidence_packet_id=decision.evidence_packet_id,
        evidence_content_hash=decision.evidence_content_hash,
        actor_subject=decision.actor_subject,
        actor_role=decision.actor_role,
        event_name=decision.action.value,
        resulting_posture=decision.resulting_posture,
        reason_codes=decision.reason_codes,
        occurred_at_utc=decision.decided_at_utc,
        suppression_reason=decision.suppression_reason,
        snoozed_until_utc=decision.snoozed_until_utc,
    )


def feedback_mutation_identity_from_command(
    candidate: IdeaCandidate,
    command: FeedbackCommand,
) -> ReviewMutationIdentity:
    return ReviewMutationIdentity(
        mutation_type=ReviewMutationType.FEEDBACK_EVENT,
        resource_id=command.feedback_id,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        actor_subject=command.actor.actor_subject,
        actor_role=command.actor.role,
        event_name=command.outcome.value,
        reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
        occurred_at_utc=command.recorded_at_utc,
        source_signal_ids=candidate.source_signal_ids,
        feedback_taxonomy_version=command.taxonomy_version,
        feedback_reason=command.reason,
    )


def feedback_mutation_identity_from_event(
    event: GovernedFeedbackEvent,
) -> ReviewMutationIdentity:
    return ReviewMutationIdentity(
        mutation_type=ReviewMutationType.FEEDBACK_EVENT,
        resource_id=event.feedback.feedback_id,
        candidate_id=event.candidate_id,
        evidence_packet_id=event.evidence_packet_id,
        evidence_content_hash=event.evidence_content_hash,
        actor_subject=event.actor_subject,
        actor_role=event.actor_role,
        event_name=event.feedback.outcome.value,
        reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
        occurred_at_utc=event.feedback.recorded_at_utc,
        source_signal_ids=event.source_signal_ids,
        feedback_taxonomy_version=event.feedback.taxonomy_version,
        feedback_reason=event.feedback.reason,
    )


def apply_review_action(
    candidate: IdeaCandidate,
    command: ReviewDecisionCommand,
    *,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> ReviewActionResult:
    _ensure_allowed(candidate, command, policy)
    updated_candidate = _candidate_after_review(candidate, command)
    decision = GovernedReviewDecision(
        review_id=command.review_id,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        action=command.action,
        resulting_posture=_REVIEW_ACTION_POSTURES[command.action],
        actor_subject=command.actor.actor_subject,
        actor_role=command.actor.role,
        reason_codes=_canonical_owned_reason_codes(
            owner_reason=_REVIEW_ACTION_REASON_CODES[command.action],
            caller_reason_codes=command.reason_codes,
        ),
        decided_at_utc=command.decided_at_utc,
        suppression_reason=command.suppression_reason,
        snoozed_until_utc=command.snoozed_until_utc,
    )
    queue_snooze = (
        QueueSnooze(
            candidate_id=candidate.candidate_id,
            snoozed_until_utc=command.snoozed_until_utc,
            reason_codes=decision.reason_codes,
        )
        if command.action is ReviewAction.SNOOZE and command.snoozed_until_utc is not None
        else None
    )
    audit_event = _review_audit_event(
        decision=decision,
        candidate_before=candidate,
        candidate_after=updated_candidate,
        outcome="accepted",
    )
    return ReviewActionResult(
        source_candidate=candidate,
        candidate=updated_candidate,
        decision=decision,
        audit_event=audit_event,
        queue_snooze=queue_snooze,
    )


def record_feedback(
    candidate: IdeaCandidate,
    command: FeedbackCommand,
    *,
    policy: ReviewActionPolicy = DEFAULT_REVIEW_ACTION_POLICY,
) -> FeedbackResult:
    _ensure_actor_scope(
        candidate_id=candidate.candidate_id,
        action=ReviewAction.NO_ACTION,
        actor=command.actor,
        access_scope=candidate.access_scope,
        policy=policy,
    )
    feedback = IdeaFeedback(
        feedback_id=command.feedback_id,
        outcome=command.outcome,
        reason=command.reason,
        taxonomy_version=command.taxonomy_version,
        actor_role=command.actor.role.value,
        recorded_at_utc=command.recorded_at_utc,
    )
    feedback_event = GovernedFeedbackEvent(
        feedback=feedback,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        source_signal_ids=candidate.source_signal_ids,
        actor_subject=command.actor.actor_subject,
        actor_role=command.actor.role,
        candidate_family=candidate.family,
        candidate_identity_policy_version=candidate.identity.policy_version,
        score_policy_version=(
            candidate.score.policy_version if candidate.score is not None else None
        ),
        score=(candidate.score.score if candidate.score is not None else None),
        evidence_supportability=candidate.evidence_packet.supportability,
        ranking_policy_version=DEFAULT_REVIEW_QUEUE_POLICY.policy_version,
        queue_priority_bucket=(
            priority_bucket_for_score(candidate.score.score)
            if candidate.score is not None
            and DEFAULT_REVIEW_QUEUE_POLICY.accepts_score_policy(candidate.score.policy_version)
            else None
        ),
    )
    audit_event = AuditEvent(
        event_type="idea.feedback.recorded",
        actor_subject=command.actor.actor_subject,
        outcome="accepted",
        occurred_at_utc=command.recorded_at_utc,
        attributes={
            "actor_role": command.actor.role.value,
            "candidate_family": candidate.family.value,
            "evidence_packet_id": candidate.evidence_packet.evidence_packet_id,
            "feedback_outcome": command.outcome.value,
            "feedback_reason": command.reason.value,
            "feedback_taxonomy_version": command.taxonomy_version,
        },
    )
    return FeedbackResult(feedback_event=feedback_event, audit_event=audit_event)


def _canonical_owned_reason_codes(
    *,
    owner_reason: ReasonCode,
    caller_reason_codes: tuple[ReasonCode, ...],
) -> tuple[ReasonCode, ...]:
    """Place an Idea-owned reason first and persist it exactly once."""
    return (
        owner_reason,
        *(reason for reason in caller_reason_codes if reason is not owner_reason),
    )


def _candidate_after_review(
    candidate: IdeaCandidate,
    command: ReviewDecisionCommand,
) -> IdeaCandidate:
    if command.action is ReviewAction.APPROVE_FOR_CONVERSION:
        _ensure_evidence_ready(candidate, command.action)
        if candidate.lifecycle_status is IdeaLifecycleStatus.READY_FOR_REVIEW:
            reviewed = transition_candidate(
                candidate,
                IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
                updated_at_utc=command.decided_at_utc,
            )
            approved = transition_candidate(
                reviewed,
                IdeaLifecycleStatus.APPROVED,
                updated_at_utc=command.decided_at_utc,
            )
        elif candidate.lifecycle_status is IdeaLifecycleStatus.REVIEWED_BY_ADVISOR:
            approved = transition_candidate(
                candidate,
                IdeaLifecycleStatus.APPROVED,
                updated_at_utc=command.decided_at_utc,
            )
        else:
            raise _invalid_review_action(candidate, command.action)
        return replace(
            approved,
            review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            updated_at_utc=command.decided_at_utc,
        )
    if command.action is ReviewAction.REJECT:
        _ensure_terminal_review_allowed(candidate, command.action)
        return replace(
            transition_candidate(
                candidate,
                IdeaLifecycleStatus.REJECTED,
                updated_at_utc=command.decided_at_utc,
            ),
            review_posture=ReviewPosture.REJECTED,
        )
    if command.action is ReviewAction.NO_ACTION:
        _ensure_terminal_review_allowed(candidate, command.action)
        return replace(
            transition_candidate(
                candidate,
                IdeaLifecycleStatus.CLOSED,
                updated_at_utc=command.decided_at_utc,
            ),
            review_posture=ReviewPosture.NO_ACTION,
        )
    if command.action is ReviewAction.SUPPRESS:
        return replace(
            candidate,
            review_posture=ReviewPosture.SUPPRESSED,
            suppression_reason=command.suppression_reason,
            updated_at_utc=command.decided_at_utc,
        )
    if command.action is ReviewAction.SNOOZE:
        return replace(candidate, updated_at_utc=command.decided_at_utc)
    if command.action is ReviewAction.ESCALATE_TO_PM:
        return replace(
            candidate,
            review_posture=ReviewPosture.PM_REVIEW_REQUIRED,
            updated_at_utc=command.decided_at_utc,
        )
    if command.action is ReviewAction.ESCALATE_TO_COMPLIANCE:
        return replace(
            candidate,
            review_posture=ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
            updated_at_utc=command.decided_at_utc,
        )
    raise _invalid_review_action(candidate, command.action)


def _ensure_allowed(
    candidate: IdeaCandidate,
    command: ReviewDecisionCommand,
    policy: ReviewActionPolicy,
) -> None:
    _ensure_actor_scope(
        candidate_id=candidate.candidate_id,
        action=command.action,
        actor=command.actor,
        access_scope=candidate.access_scope,
        policy=policy,
    )
    if candidate.lifecycle_status not in _REVIEW_ACTION_LIFECYCLE_STATUSES[command.action]:
        raise _invalid_review_action(candidate, command.action)


def _ensure_actor_scope(
    *,
    candidate_id: str,
    action: ReviewAction,
    actor: ReviewActorContext,
    access_scope: ReviewAccessScope | None,
    policy: ReviewActionPolicy,
) -> None:
    if (
        access_scope is None
        or not actor.can_access(access_scope)
        or not policy.allows(actor, action)
    ):
        raise ReviewEntitlementDenied(candidate_id)


def _ensure_evidence_ready(candidate: IdeaCandidate, action: ReviewAction) -> None:
    if candidate.evidence_packet.supportability is not EvidenceSupportability.READY:
        raise _invalid_review_action(candidate, action)


def _ensure_terminal_review_allowed(candidate: IdeaCandidate, action: ReviewAction) -> None:
    if candidate.lifecycle_status not in _DECISION_LIFECYCLE_STATUSES:
        raise _invalid_review_action(candidate, action)


def _invalid_review_action(
    candidate: IdeaCandidate,
    action: ReviewAction,
) -> InvalidReviewAction:
    return InvalidReviewAction(
        action,
        candidate.lifecycle_status,
        candidate.review_posture,
    )


def _review_audit_event(
    *,
    decision: GovernedReviewDecision,
    candidate_before: IdeaCandidate,
    candidate_after: IdeaCandidate,
    outcome: str,
) -> AuditEvent:
    return AuditEvent(
        event_type="idea.review.decision_recorded",
        actor_subject=decision.actor_subject,
        outcome=outcome,
        occurred_at_utc=decision.decided_at_utc,
        attributes={
            "actor_role": decision.actor_role.value,
            "candidate_id": candidate_before.candidate_id,
            "candidate_family": candidate_before.family.value,
            "evidence_packet_id": decision.evidence_packet_id,
            "policy_version": CANDIDATE_STATE_POLICY_VERSION,
            "prior_lifecycle_status": candidate_before.lifecycle_status.value,
            "prior_review_posture": candidate_before.review_posture.value,
            "requested_action": decision.action.value,
            "reason_codes": ",".join(reason.value for reason in decision.reason_codes),
            "review_action": decision.action.value,
            "review_posture": candidate_after.review_posture.value,
        },
    )
