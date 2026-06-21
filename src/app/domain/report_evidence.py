from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.audit import AuditEvent
from app.domain.conversion_governance import GovernedConversionIntent
from app.domain.ideas import (
    ConversionTarget,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    SourceSystem,
)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class ReportEvidencePackBoundary(StrEnum):
    REQUEST_ONLY = "request_only"
    DOWNSTREAM_MATERIALIZATION_REQUIRED = "downstream_materialization_required"


class ReportEvidencePackPurpose(StrEnum):
    CLIENT_REVIEW_REPORT_SECTION = "client_review_report_section"
    ADVISOR_REVIEW_EVIDENCE = "advisor_review_evidence"
    AUDIT_EVIDENCE = "audit_evidence"


class InvalidReportEvidencePack(ValueError):
    def __init__(self, conversion_intent_id: str, reason: str) -> None:
        super().__init__(
            f"Invalid report evidence pack for conversion intent {conversion_intent_id}: {reason}"
        )
        self.conversion_intent_id = conversion_intent_id
        self.reason = reason


@dataclass(frozen=True)
class ReportEvidencePackCommand:
    report_evidence_pack_id: str
    purpose: ReportEvidencePackPurpose
    actor_subject: str
    idempotency_key: str
    reason_codes: tuple[ReasonCode, ...]
    requested_at_utc: datetime
    retention_policy_ref: str
    client_ready_publication_requested: bool = False

    def __post_init__(self) -> None:
        _require_text(self.report_evidence_pack_id, "report_evidence_pack_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_text(self.retention_policy_ref, "retention_policy_ref")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ReportEvidenceSourceSummary:
    product_id: str
    source_system: SourceSystem
    product_version: str
    as_of_date: str
    generated_at_utc: datetime
    content_hash: str
    data_quality_status: str
    freshness: str

    @classmethod
    def from_source_ref(cls, source_ref: SourceRef) -> "ReportEvidenceSourceSummary":
        return cls(
            product_id=source_ref.product_id,
            source_system=source_ref.source_system,
            product_version=source_ref.product_version,
            as_of_date=source_ref.as_of_date.isoformat(),
            generated_at_utc=source_ref.generated_at_utc,
            content_hash=source_ref.content_hash,
            data_quality_status=source_ref.data_quality_status,
            freshness=source_ref.freshness.value,
        )


@dataclass(frozen=True)
class GovernedReportEvidencePack:
    report_evidence_pack_id: str
    conversion_intent_id: str
    candidate_id: str
    evidence_packet_id: str
    evidence_content_hash: str
    source_signal_ids: tuple[str, ...]
    source_summaries: tuple[ReportEvidenceSourceSummary, ...]
    purpose: ReportEvidencePackPurpose
    actor_subject: str
    idempotency_key: str
    reason_codes: tuple[ReasonCode, ...]
    requested_at_utc: datetime
    retention_policy_ref: str
    report_source_authority: SourceSystem = SourceSystem.LOTUS_REPORT
    render_source_authority: SourceSystem = SourceSystem.LOTUS_RENDER
    archive_source_authority: SourceSystem = SourceSystem.LOTUS_ARCHIVE
    boundary: ReportEvidencePackBoundary = ReportEvidencePackBoundary.REQUEST_ONLY

    @property
    def grants_client_publication_authority(self) -> bool:
        return False

    @property
    def creates_rendered_output(self) -> bool:
        return False

    @property
    def creates_archive_record(self) -> bool:
        return False

    def __post_init__(self) -> None:
        _require_text(self.report_evidence_pack_id, "report_evidence_pack_id")
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_text(self.evidence_content_hash, "evidence_content_hash")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_text(self.retention_policy_ref, "retention_policy_ref")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        if not self.source_signal_ids:
            raise ValueError("source_signal_ids is required")
        if not self.source_summaries:
            raise ValueError("source_summaries is required")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "source_signal_ids", tuple(self.source_signal_ids))
        object.__setattr__(self, "source_summaries", tuple(self.source_summaries))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ReportEvidencePackResult:
    evidence_pack: GovernedReportEvidencePack
    audit_event: AuditEvent


def request_report_evidence_pack(
    candidate: IdeaCandidate,
    conversion_intent: GovernedConversionIntent,
    command: ReportEvidencePackCommand,
) -> ReportEvidencePackResult:
    _ensure_report_evidence_pack_allowed(candidate, conversion_intent, command)
    evidence_pack = GovernedReportEvidencePack(
        report_evidence_pack_id=command.report_evidence_pack_id,
        conversion_intent_id=conversion_intent.intent.conversion_intent_id,
        candidate_id=candidate.candidate_id,
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        source_signal_ids=candidate.source_signal_ids,
        source_summaries=tuple(
            ReportEvidenceSourceSummary.from_source_ref(source_ref)
            for source_ref in candidate.evidence_packet.source_refs
        ),
        purpose=command.purpose,
        actor_subject=command.actor_subject,
        idempotency_key=command.idempotency_key,
        reason_codes=command.reason_codes,
        requested_at_utc=command.requested_at_utc,
        retention_policy_ref=command.retention_policy_ref,
    )
    audit_event = AuditEvent(
        event_type="idea.report_evidence_pack.requested",
        actor_subject=command.actor_subject,
        outcome="accepted",
        occurred_at_utc=command.requested_at_utc,
        attributes={
            "boundary": evidence_pack.boundary.value,
            "candidate_family": candidate.family.value,
            "conversion_intent_id": conversion_intent.intent.conversion_intent_id,
            "evidence_packet_id": evidence_pack.evidence_packet_id,
            "purpose": command.purpose.value,
            "report_source_authority": evidence_pack.report_source_authority.value,
        },
    )
    return ReportEvidencePackResult(evidence_pack=evidence_pack, audit_event=audit_event)


def _ensure_report_evidence_pack_allowed(
    candidate: IdeaCandidate,
    conversion_intent: GovernedConversionIntent,
    command: ReportEvidencePackCommand,
) -> None:
    intent_id = conversion_intent.intent.conversion_intent_id
    if command.client_ready_publication_requested:
        raise InvalidReportEvidencePack(intent_id, "client-ready publication is not authorized")
    if conversion_intent.intent.target is not ConversionTarget.REPORT_EVIDENCE:
        raise InvalidReportEvidencePack(intent_id, "conversion target is not report evidence")
    if conversion_intent.intent.candidate_id != candidate.candidate_id:
        raise InvalidReportEvidencePack(intent_id, "conversion intent candidate mismatch")
    if conversion_intent.target_source_authority is not SourceSystem.LOTUS_REPORT:
        raise InvalidReportEvidencePack(intent_id, "target source authority is not lotus-report")
    if candidate.lifecycle_status is not IdeaLifecycleStatus.CONVERTED_TO_REPORT:
        raise InvalidReportEvidencePack(intent_id, "candidate lifecycle is not converted to report")
    if candidate.review_posture is not ReviewPosture.APPROVED_FOR_CONVERSION:
        raise InvalidReportEvidencePack(intent_id, "review posture is not approved")
    if candidate.evidence_packet.supportability is not EvidenceSupportability.READY:
        raise InvalidReportEvidencePack(intent_id, "evidence is not ready")
    if (
        candidate.evidence_packet.lineage_ref.content_hash
        != conversion_intent.evidence_content_hash
    ):
        raise InvalidReportEvidencePack(intent_id, "evidence hash does not match conversion intent")
