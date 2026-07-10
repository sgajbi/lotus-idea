from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.audit import AuditEvent
from app.domain.conversion_outcome_policy import (
    CONVERSION_OUTCOME_POLICY_VERSION,
    ConversionOutcomeIdentity,
    ConversionOutcomePolicyViolation,
    current_conversion_outcome_identity,
    validate_conversion_outcome_progression,
)
from app.domain.ideas import (
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaConversionIntent,
    IdeaConversionOutcome,
    IdeaLifecycleStatus,
    ReasonCode,
    ReviewPosture,
    SourceSystem,
    transition_candidate,
)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class InvalidConversionIntent(ValueError):
    def __init__(self, candidate_id: str, reason: str) -> None:
        super().__init__(f"Invalid conversion intent for candidate {candidate_id}: {reason}")
        self.candidate_id = candidate_id
        self.reason = reason


class InvalidConversionOutcome(ValueError):
    def __init__(self, conversion_intent_id: str, reason: str) -> None:
        super().__init__(f"Invalid conversion outcome for intent {conversion_intent_id}: {reason}")
        self.conversion_intent_id = conversion_intent_id
        self.reason = reason


class ConversionBoundary(StrEnum):
    INTENT_ONLY = "intent_only"
    DOWNSTREAM_REALIZATION_REQUIRED = "downstream_realization_required"


TARGET_SOURCE_AUTHORITIES: dict[ConversionTarget, SourceSystem] = {
    ConversionTarget.ADVISE_PROPOSAL: SourceSystem.LOTUS_ADVISE,
    ConversionTarget.MANAGE_REVIEW: SourceSystem.LOTUS_MANAGE,
    ConversionTarget.REPORT_EVIDENCE: SourceSystem.LOTUS_REPORT,
}

TARGET_LIFECYCLE_STATUS: dict[ConversionTarget, IdeaLifecycleStatus] = {
    ConversionTarget.ADVISE_PROPOSAL: IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL,
    ConversionTarget.MANAGE_REVIEW: IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW,
    ConversionTarget.REPORT_EVIDENCE: IdeaLifecycleStatus.CONVERTED_TO_REPORT,
}


@dataclass(frozen=True)
class ConversionIntentCommand:
    conversion_intent_id: str
    target: ConversionTarget
    actor_subject: str
    idempotency_key: str
    reason_codes: tuple[ReasonCode, ...]
    requested_at_utc: datetime

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class GovernedConversionIntent:
    intent: IdeaConversionIntent
    evidence_packet_id: str
    evidence_content_hash: str
    source_signal_ids: tuple[str, ...]
    actor_subject: str
    idempotency_key: str
    reason_codes: tuple[ReasonCode, ...]
    target_source_authority: SourceSystem
    boundary: ConversionBoundary = ConversionBoundary.INTENT_ONLY

    @property
    def grants_downstream_authority(self) -> bool:
        return False

    def __post_init__(self) -> None:
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_text(self.evidence_content_hash, "evidence_content_hash")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(self.idempotency_key, "idempotency_key")
        if not self.source_signal_ids:
            raise ValueError("source_signal_ids is required")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "source_signal_ids", tuple(self.source_signal_ids))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ConversionIntentResult:
    candidate: IdeaCandidate
    conversion_intent: GovernedConversionIntent
    audit_event: AuditEvent


@dataclass(frozen=True)
class ConversionOutcomeCommand:
    conversion_outcome_id: str
    status: ConversionOutcomeStatus
    source_system: SourceSystem
    source_event_version: int
    recorded_at_utc: datetime
    downstream_reference: str | None = None
    actor_subject: str = "downstream-system"
    supersedes_conversion_outcome_id: str | None = None
    correction_reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_outcome_id, "conversion_outcome_id")
        _require_text(self.actor_subject, "actor_subject")
        if self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive")
        _require_aware_utc(self.recorded_at_utc, "recorded_at_utc")
        if self.downstream_reference is not None:
            _require_text(self.downstream_reference, "downstream_reference")
        if self.supersedes_conversion_outcome_id is not None:
            _require_text(
                self.supersedes_conversion_outcome_id,
                "supersedes_conversion_outcome_id",
            )
        if self.correction_reason is not None:
            _require_text(self.correction_reason, "correction_reason")


@dataclass(frozen=True)
class GovernedConversionOutcome:
    outcome: IdeaConversionOutcome
    conversion_intent_id: str
    target: ConversionTarget
    source_system: SourceSystem
    boundary: ConversionBoundary
    source_event_version: int
    actor_subject: str
    supersedes_conversion_outcome_id: str | None = None
    correction_reason: str | None = None

    @property
    def identity(self) -> ConversionOutcomeIdentity:
        return ConversionOutcomeIdentity(
            conversion_outcome_id=self.outcome.conversion_outcome_id,
            conversion_intent_id=self.conversion_intent_id,
            target=self.target,
            source_system=self.source_system,
            source_event_version=self.source_event_version,
            status=self.outcome.status,
            downstream_reference=self.outcome.downstream_reference,
            recorded_at_utc=self.outcome.recorded_at_utc,
            actor_subject=self.actor_subject,
            supersedes_conversion_outcome_id=self.supersedes_conversion_outcome_id,
            correction_reason=self.correction_reason,
        )

    @property
    def grants_execution_authority(self) -> bool:
        return False

    @property
    def grants_client_communication_authority(self) -> bool:
        return False

    @property
    def grants_suitability_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class ConversionOutcomeResult:
    conversion_outcome: GovernedConversionOutcome
    audit_event: AuditEvent


def request_conversion_intent(
    candidate: IdeaCandidate,
    command: ConversionIntentCommand,
) -> ConversionIntentResult:
    _ensure_candidate_ready_for_conversion(candidate)
    intent = IdeaConversionIntent(
        conversion_intent_id=command.conversion_intent_id,
        candidate_id=candidate.candidate_id,
        target=command.target,
        source_status=candidate.lifecycle_status,
        requested_at_utc=command.requested_at_utc,
    )
    governed_intent = GovernedConversionIntent(
        intent=intent,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        source_signal_ids=candidate.source_signal_ids,
        actor_subject=command.actor_subject,
        idempotency_key=command.idempotency_key,
        reason_codes=command.reason_codes,
        target_source_authority=TARGET_SOURCE_AUTHORITIES[command.target],
    )
    transitioned_candidate = transition_candidate(
        candidate,
        TARGET_LIFECYCLE_STATUS[command.target],
        updated_at_utc=command.requested_at_utc,
    )
    audit_event = AuditEvent(
        event_type="idea.conversion.intent_requested",
        actor_subject=command.actor_subject,
        outcome="accepted",
        occurred_at_utc=command.requested_at_utc,
        attributes={
            "boundary": governed_intent.boundary.value,
            "candidate_family": candidate.family.value,
            "conversion_target": command.target.value,
            "evidence_packet_id": candidate.evidence_packet.evidence_packet_id,
            "target_source_authority": governed_intent.target_source_authority.value,
        },
    )
    return ConversionIntentResult(
        candidate=transitioned_candidate,
        conversion_intent=governed_intent,
        audit_event=audit_event,
    )


def record_conversion_outcome(
    governed_intent: GovernedConversionIntent,
    command: ConversionOutcomeCommand,
    *,
    existing_outcomes: tuple[GovernedConversionOutcome, ...] = (),
) -> ConversionOutcomeResult:
    expected_source = TARGET_SOURCE_AUTHORITIES[governed_intent.intent.target]
    if command.source_system is not expected_source:
        raise InvalidConversionOutcome(
            governed_intent.intent.conversion_intent_id,
            f"outcome source must be {expected_source.value}",
        )
    if (
        command.status
        in {
            ConversionOutcomeStatus.ACCEPTED,
            ConversionOutcomeStatus.COMPLETED,
        }
        and command.downstream_reference is None
    ):
        raise InvalidConversionOutcome(
            governed_intent.intent.conversion_intent_id,
            "accepted or completed outcome requires downstream reference",
        )
    outcome = IdeaConversionOutcome(
        conversion_outcome_id=command.conversion_outcome_id,
        conversion_intent_id=governed_intent.intent.conversion_intent_id,
        status=command.status,
        downstream_reference=command.downstream_reference,
        recorded_at_utc=command.recorded_at_utc,
    )
    governed_outcome = GovernedConversionOutcome(
        outcome=outcome,
        conversion_intent_id=governed_intent.intent.conversion_intent_id,
        target=governed_intent.intent.target,
        source_system=command.source_system,
        boundary=ConversionBoundary.DOWNSTREAM_REALIZATION_REQUIRED,
        source_event_version=command.source_event_version,
        actor_subject=command.actor_subject,
        supersedes_conversion_outcome_id=command.supersedes_conversion_outcome_id,
        correction_reason=command.correction_reason,
    )
    try:
        validate_conversion_outcome_progression(
            tuple(outcome.identity for outcome in existing_outcomes),
            governed_outcome.identity,
        )
    except ConversionOutcomePolicyViolation as exc:
        raise InvalidConversionOutcome(
            governed_intent.intent.conversion_intent_id,
            exc.reason.value,
        ) from exc
    audit_event = AuditEvent(
        event_type="idea.conversion.outcome_recorded",
        actor_subject=command.actor_subject,
        outcome="accepted",
        occurred_at_utc=command.recorded_at_utc,
        attributes={
            "boundary": governed_outcome.boundary.value,
            "conversion_status": command.status.value,
            "conversion_target": governed_intent.intent.target.value,
            "source_system": command.source_system.value,
            "source_event_version": str(command.source_event_version),
            "policy_version": CONVERSION_OUTCOME_POLICY_VERSION,
            "supersedes_outcome": str(command.supersedes_conversion_outcome_id is not None).lower(),
        },
    )
    return ConversionOutcomeResult(conversion_outcome=governed_outcome, audit_event=audit_event)


def conversion_outcome_identity_from_command(
    governed_intent: GovernedConversionIntent,
    command: ConversionOutcomeCommand,
) -> ConversionOutcomeIdentity:
    return ConversionOutcomeIdentity(
        conversion_outcome_id=command.conversion_outcome_id,
        conversion_intent_id=governed_intent.intent.conversion_intent_id,
        target=governed_intent.intent.target,
        source_system=command.source_system,
        source_event_version=command.source_event_version,
        status=command.status,
        downstream_reference=command.downstream_reference,
        recorded_at_utc=command.recorded_at_utc,
        actor_subject=command.actor_subject,
        supersedes_conversion_outcome_id=command.supersedes_conversion_outcome_id,
        correction_reason=command.correction_reason,
    )


def current_conversion_outcome(
    outcomes: tuple[GovernedConversionOutcome, ...],
) -> GovernedConversionOutcome | None:
    current = current_conversion_outcome_identity(tuple(outcome.identity for outcome in outcomes))
    if current is None:
        return None
    return next(outcome for outcome in outcomes if outcome.identity == current)


def _ensure_candidate_ready_for_conversion(candidate: IdeaCandidate) -> None:
    if candidate.lifecycle_status is not IdeaLifecycleStatus.APPROVED:
        raise InvalidConversionIntent(candidate.candidate_id, "candidate lifecycle is not approved")
    if candidate.review_posture is not ReviewPosture.APPROVED_FOR_CONVERSION:
        raise InvalidConversionIntent(candidate.candidate_id, "review posture is not approved")
    if candidate.evidence_packet.supportability is not EvidenceSupportability.READY:
        raise InvalidConversionIntent(candidate.candidate_id, "evidence is not ready")
