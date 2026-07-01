from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.access_scope import ReviewAccessScope


class OpportunityFamily(StrEnum):
    HIGH_CASH = "high_cash"
    CONCENTRATION = "concentration"
    UNDERPERFORMANCE = "underperformance"
    ALLOCATION_DRIFT = "allocation_drift"
    BOND_MATURITY = "bond_maturity"
    LOW_INCOME = "low_income"
    HIGH_VOLATILITY = "high_volatility"
    MISSING_BENCHMARK = "missing_benchmark"
    MISSING_RISK_PROFILE = "missing_risk_profile"
    MISSING_SUITABILITY_CONTEXT = "missing_suitability_context"
    MANDATE_RESTRICTION = "mandate_restriction"


class SourceSystem(StrEnum):
    LOTUS_CORE = "lotus-core"
    LOTUS_PERFORMANCE = "lotus-performance"
    LOTUS_RISK = "lotus-risk"
    LOTUS_ADVISE = "lotus-advise"
    LOTUS_MANAGE = "lotus-manage"
    LOTUS_REPORT = "lotus-report"
    LOTUS_RENDER = "lotus-render"
    LOTUS_ARCHIVE = "lotus-archive"
    LOTUS_AI = "lotus-ai"


class EvidenceFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"


class EvidenceSupportability(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class UnsupportedEvidenceReason(StrEnum):
    MISSING_SOURCE = "missing_source"
    STALE_SOURCE = "stale_source"
    SOURCE_UNAVAILABLE = "source_unavailable"
    SOURCE_UNCERTIFIED = "source_uncertified"
    ENTITLEMENT_DENIED = "entitlement_denied"
    INCOMPLETE_LINEAGE = "incomplete_lineage"
    UNSUPPORTED_SOURCE_PRODUCT = "unsupported_source_product"
    HASH_MISMATCH = "hash_mismatch"
    AI_UNAVAILABLE = "ai_unavailable"
    UNSUPPORTED_AI_CLAIM = "unsupported_ai_claim"


class ReasonCode(StrEnum):
    HIGH_CASH_RATIO = "high_cash_ratio"
    CASH_SOURCE_READY = "cash_source_ready"
    CONCENTRATION_ATTENTION = "concentration_attention"
    UNDERPERFORMANCE_ATTENTION = "underperformance_attention"
    ALLOCATION_DRIFT_ATTENTION = "allocation_drift_attention"
    MATURITY_WINDOW = "maturity_window"
    INCOME_ATTENTION = "income_attention"
    VOLATILITY_ATTENTION = "volatility_attention"
    DRAWDOWN_ATTENTION = "drawdown_attention"
    MISSING_BENCHMARK = "missing_benchmark"
    MISSING_RISK_PROFILE = "missing_risk_profile"
    SUITABILITY_CONTEXT_MISSING = "suitability_context_missing"
    MANDATE_RESTRICTION_REVIEW = "mandate_restriction_review"
    SOURCE_STALE = "source_stale"
    SOURCE_PARTIAL = "source_partial"
    DUPLICATE_SUPPRESSED = "duplicate_suppressed"
    BELOW_MATERIALITY = "below_materiality"
    REVIEW_REQUIRED = "review_required"
    MATERIALITY_SCORE = "materiality_score"
    URGENCY_SCORE = "urgency_score"
    CONFIDENCE_SCORE = "confidence_score"
    EVIDENCE_QUALITY_SCORE = "evidence_quality_score"
    FRESHNESS_SCORE = "freshness_score"
    RELEVANCE_SCORE = "relevance_score"
    DOWNSTREAM_FIT_SCORE = "downstream_fit_score"
    CONFLICT_PENALTY = "conflict_penalty"
    QUEUE_PRIORITY = "queue_priority"
    QUEUE_EXCLUDED = "queue_excluded"
    REVIEW_APPROVED_FOR_CONVERSION = "review_approved_for_conversion"
    REVIEW_REJECTED = "review_rejected"
    REVIEW_NO_ACTION = "review_no_action"
    REVIEW_SUPPRESSED = "review_suppressed"
    REVIEW_SNOOZED = "review_snoozed"
    REVIEW_ESCALATED = "review_escalated"
    FEEDBACK_RECORDED = "feedback_recorded"
    ENTITLEMENT_DENIED = "entitlement_denied"
    AI_REDACTION_APPLIED = "ai_redaction_applied"
    AI_FALLBACK_USED = "ai_fallback_used"
    AI_VERIFIER_PASSED = "ai_verifier_passed"
    AI_UNSUPPORTED_CLAIM_BLOCKED = "ai_unsupported_claim_blocked"
    AI_FORBIDDEN_ACTION_BLOCKED = "ai_forbidden_action_blocked"


class IdeaLifecycleStatus(StrEnum):
    DETECTED = "detected"
    GENERATED = "generated"
    ENRICHED = "enriched"
    SCORED = "scored"
    GOVERNANCE_CHECKED = "governance_checked"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED_BY_ADVISOR = "reviewed_by_advisor"
    APPROVED = "approved"
    CONVERTED_TO_PROPOSAL = "converted_to_proposal"
    CONVERTED_TO_MANAGE_REVIEW = "converted_to_manage_review"
    CONVERTED_TO_REPORT = "converted_to_report"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    CLOSED = "closed"


DOWNSTREAM_AUTHORITY_LIFECYCLE_STATUSES = frozenset(
    {
        IdeaLifecycleStatus.ACCEPTED,
        IdeaLifecycleStatus.EXECUTED,
    }
)
CALLER_SETTABLE_LIFECYCLE_STATUSES = frozenset(
    status
    for status in IdeaLifecycleStatus
    if status not in DOWNSTREAM_AUTHORITY_LIFECYCLE_STATUSES
)


def validate_caller_settable_lifecycle_status(target_status: IdeaLifecycleStatus) -> None:
    if target_status in DOWNSTREAM_AUTHORITY_LIFECYCLE_STATUSES:
        raise ValueError(
            f"{target_status.value} is reserved for downstream source-authority outcomes "
            "and cannot be set through idea lifecycle transitions"
        )


class ReviewPosture(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    ADVISOR_REVIEW_REQUIRED = "advisor_review_required"
    ADVISOR_REVIEWED = "advisor_reviewed"
    APPROVED_FOR_CONVERSION = "approved_for_conversion"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"
    NO_ACTION = "no_action"
    PM_REVIEW_REQUIRED = "pm_review_required"
    COMPLIANCE_REVIEW_REQUIRED = "compliance_review_required"


class SuppressionReason(StrEnum):
    DUPLICATE = "duplicate"
    RECENTLY_REJECTED = "recently_rejected"
    BELOW_MATERIALITY = "below_materiality"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    MANUAL_SUPPRESSION = "manual_suppression"


class FeedbackOutcome(StrEnum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    DUPLICATE = "duplicate"
    TOO_LATE = "too_late"
    MISSING_CONTEXT = "missing_context"
    UNSUPPORTED_CLAIM = "unsupported_claim"


class ConversionTarget(StrEnum):
    ADVISE_PROPOSAL = "advise_proposal"
    MANAGE_REVIEW = "manage_review"
    REPORT_EVIDENCE = "report_evidence"


class ConversionOutcomeStatus(StrEnum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    COMPLETED = "completed"


class InvalidLifecycleTransition(ValueError):
    def __init__(self, source: IdeaLifecycleStatus, target: IdeaLifecycleStatus) -> None:
        super().__init__(f"Invalid idea lifecycle transition: {source} -> {target}")
        self.source = source
        self.target = target


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class SourceRef:
    product_id: str
    source_system: SourceSystem
    product_version: str
    route: str
    as_of_date: date
    generated_at_utc: datetime
    content_hash: str
    data_quality_status: str
    freshness: EvidenceFreshness

    def __post_init__(self) -> None:
        _require_text(self.product_id, "product_id")
        _require_text(self.product_version, "product_version")
        _require_text(self.route, "route")
        _require_text(self.content_hash, "content_hash")
        _require_text(self.data_quality_status, "data_quality_status")
        _require_aware_utc(self.generated_at_utc, "generated_at_utc")


@dataclass(frozen=True)
class LineageRef:
    lineage_id: str
    source_refs: tuple[SourceRef, ...]
    content_hash: str

    def __post_init__(self) -> None:
        _require_text(self.lineage_id, "lineage_id")
        _require_text(self.content_hash, "content_hash")
        if not self.source_refs:
            raise ValueError("source_refs is required")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))


@dataclass(frozen=True)
class OpportunitySignal:
    signal_id: str
    family: OpportunityFamily
    source_refs: tuple[SourceRef, ...]
    reason_codes: tuple[ReasonCode, ...]
    detected_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.signal_id, "signal_id")
        _require_aware_utc(self.detected_at_utc, "detected_at_utc")
        if self.expires_at_utc is not None:
            _require_aware_utc(self.expires_at_utc, "expires_at_utc")
        if not self.source_refs:
            raise ValueError("source_refs is required")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class IdeaEvidencePacket:
    evidence_packet_id: str
    supportability: EvidenceSupportability
    source_refs: tuple[SourceRef, ...]
    lineage_ref: LineageRef
    reason_codes: tuple[ReasonCode, ...]
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...] = ()
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_aware_utc(self.created_at_utc, "created_at_utc")
        if not self.source_refs:
            raise ValueError("source_refs is required")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.supportability is EvidenceSupportability.BLOCKED and not self.unsupported_reasons:
            raise ValueError("blocked evidence requires unsupported_reasons")
        if self.supportability is EvidenceSupportability.READY and self.unsupported_reasons:
            raise ValueError("ready evidence cannot carry unsupported_reasons")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "unsupported_reasons", tuple(self.unsupported_reasons))


@dataclass(frozen=True)
class IdeaScore:
    policy_version: str
    score: Decimal
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        if self.score < Decimal("0") or self.score > Decimal("100"):
            raise ValueError("score must be between 0 and 100")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ReviewDecision:
    review_id: str
    posture: ReviewPosture
    reviewer_role: str
    reason_codes: tuple[ReasonCode, ...]
    decided_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def grants_downstream_authority(self) -> bool:
        return False

    def __post_init__(self) -> None:
        _require_text(self.review_id, "review_id")
        _require_text(self.reviewer_role, "reviewer_role")
        _require_aware_utc(self.decided_at_utc, "decided_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class IdeaFeedback:
    feedback_id: str
    outcome: FeedbackOutcome
    actor_role: str
    reason_codes: tuple[ReasonCode, ...]
    recorded_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.feedback_id, "feedback_id")
        _require_text(self.actor_role, "actor_role")
        _require_aware_utc(self.recorded_at_utc, "recorded_at_utc")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class IdeaCandidate:
    candidate_id: str
    family: OpportunityFamily
    lifecycle_status: IdeaLifecycleStatus
    review_posture: ReviewPosture
    evidence_packet: IdeaEvidencePacket
    source_signal_ids: tuple[str, ...]
    score: IdeaScore | None = None
    access_scope: ReviewAccessScope | None = None
    suppression_reason: SuppressionReason | None = None
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def ready_for_conversion(self) -> bool:
        return (
            self.lifecycle_status is IdeaLifecycleStatus.APPROVED
            and self.review_posture is ReviewPosture.APPROVED_FOR_CONVERSION
            and self.evidence_packet.supportability is EvidenceSupportability.READY
        )

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_aware_utc(self.created_at_utc, "created_at_utc")
        _require_aware_utc(self.updated_at_utc, "updated_at_utc")
        if not self.source_signal_ids:
            raise ValueError("source_signal_ids is required")
        object.__setattr__(self, "source_signal_ids", tuple(self.source_signal_ids))


@dataclass(frozen=True)
class IdeaConversionIntent:
    conversion_intent_id: str
    candidate_id: str
    target: ConversionTarget
    source_status: IdeaLifecycleStatus
    requested_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        if self.source_status is not IdeaLifecycleStatus.APPROVED:
            raise ValueError("conversion intent requires approved source_status")


@dataclass(frozen=True)
class IdeaConversionOutcome:
    conversion_outcome_id: str
    conversion_intent_id: str
    status: ConversionOutcomeStatus
    downstream_reference: str | None = None
    recorded_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.conversion_outcome_id, "conversion_outcome_id")
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_aware_utc(self.recorded_at_utc, "recorded_at_utc")
        if self.downstream_reference is not None:
            _require_text(self.downstream_reference, "downstream_reference")


ALLOWED_LIFECYCLE_TRANSITIONS: dict[IdeaLifecycleStatus, frozenset[IdeaLifecycleStatus]] = {
    IdeaLifecycleStatus.DETECTED: frozenset(
        {
            IdeaLifecycleStatus.GENERATED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.GENERATED: frozenset(
        {
            IdeaLifecycleStatus.ENRICHED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.ENRICHED: frozenset(
        {
            IdeaLifecycleStatus.SCORED,
            IdeaLifecycleStatus.GOVERNANCE_CHECKED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.SCORED: frozenset(
        {
            IdeaLifecycleStatus.GOVERNANCE_CHECKED,
            IdeaLifecycleStatus.READY_FOR_REVIEW,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.GOVERNANCE_CHECKED: frozenset(
        {
            IdeaLifecycleStatus.READY_FOR_REVIEW,
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.READY_FOR_REVIEW: frozenset(
        {
            IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.REVIEWED_BY_ADVISOR: frozenset(
        {
            IdeaLifecycleStatus.APPROVED,
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.APPROVED: frozenset(
        {
            IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL,
            IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW,
            IdeaLifecycleStatus.CONVERTED_TO_REPORT,
            IdeaLifecycleStatus.EXPIRED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL: frozenset(
        {
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW: frozenset(
        {
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.CONVERTED_TO_REPORT: frozenset(
        {
            IdeaLifecycleStatus.REJECTED,
            IdeaLifecycleStatus.CLOSED,
        }
    ),
    IdeaLifecycleStatus.ACCEPTED: frozenset({IdeaLifecycleStatus.CLOSED}),
    IdeaLifecycleStatus.REJECTED: frozenset({IdeaLifecycleStatus.CLOSED}),
    IdeaLifecycleStatus.EXPIRED: frozenset({IdeaLifecycleStatus.CLOSED}),
    IdeaLifecycleStatus.EXECUTED: frozenset({IdeaLifecycleStatus.CLOSED}),
    IdeaLifecycleStatus.CLOSED: frozenset(),
}


def transition_candidate(
    candidate: IdeaCandidate,
    target_status: IdeaLifecycleStatus,
    *,
    updated_at_utc: datetime | None = None,
) -> IdeaCandidate:
    allowed_targets = ALLOWED_LIFECYCLE_TRANSITIONS[candidate.lifecycle_status]
    if target_status not in allowed_targets:
        raise InvalidLifecycleTransition(candidate.lifecycle_status, target_status)
    return replace(
        candidate,
        lifecycle_status=target_status,
        updated_at_utc=updated_at_utc or datetime.now(UTC),
    )
