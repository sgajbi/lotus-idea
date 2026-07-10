from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.domain import (
    CandidatePersistenceRecord,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    GovernedFeedbackEvent,
    GovernedReportEvidencePack,
    GovernedReviewDecision,
    LifecycleHistoryEntry,
    SourceRef,
    current_conversion_outcome,
)


class CandidateDetailCandidateResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    supportability: str
    score: str | None = None
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    suppression_reason: str | None = Field(default=None, alias="suppressionReason")
    created_at_utc: datetime = Field(..., alias="createdAtUtc")
    updated_at_utc: datetime = Field(..., alias="updatedAtUtc")

    @classmethod
    def from_record(cls, record: CandidatePersistenceRecord) -> "CandidateDetailCandidateResponse":
        candidate = record.candidate
        score = candidate.score
        return cls(
            candidateId=candidate.candidate_id,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            supportability=candidate.evidence_packet.supportability.value,
            score=(str(score.score) if score is not None else None),
            scorePolicyVersion=(score.policy_version if score is not None else None),
            sourceSignalIds=candidate.source_signal_ids,
            reasonCodes=tuple(reason.value for reason in candidate.evidence_packet.reason_codes),
            unsupportedReasons=tuple(
                reason.value for reason in candidate.evidence_packet.unsupported_reasons
            ),
            suppressionReason=(
                candidate.suppression_reason.value
                if candidate.suppression_reason is not None
                else None
            ),
            createdAtUtc=candidate.created_at_utc,
            updatedAtUtc=candidate.updated_at_utc,
        )


class RedactedSourceRefResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: str = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: date = Field(..., alias="asOfDate")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    freshness: str

    @classmethod
    def from_domain(cls, source_ref: SourceRef) -> "RedactedSourceRefResponse":
        return cls(
            productId=source_ref.product_id,
            sourceSystem=source_ref.source_system.value,
            productVersion=source_ref.product_version,
            asOfDate=source_ref.as_of_date,
            generatedAtUtc=source_ref.generated_at_utc,
            dataQualityStatus=source_ref.data_quality_status,
            freshness=source_ref.freshness.value,
        )


class CandidateEvidenceResponse(CamelModel):
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    supportability: str
    lineage_id: str = Field(..., alias="lineageId")
    created_at_utc: datetime = Field(..., alias="createdAtUtc")
    source_refs: tuple[RedactedSourceRefResponse, ...] = Field(..., alias="sourceRefs")

    @classmethod
    def from_record(cls, record: CandidatePersistenceRecord) -> "CandidateEvidenceResponse":
        evidence_packet = record.candidate.evidence_packet
        return cls(
            evidencePacketId=evidence_packet.evidence_packet_id,
            evidenceContentHash=record.evidence_hash,
            supportability=evidence_packet.supportability.value,
            lineageId=evidence_packet.lineage_ref.lineage_id,
            createdAtUtc=evidence_packet.created_at_utc,
            sourceRefs=tuple(
                RedactedSourceRefResponse.from_domain(source_ref)
                for source_ref in evidence_packet.source_refs
            ),
        )


class LifecycleHistoryResponse(CamelModel):
    source_status: str = Field(..., alias="sourceStatus")
    target_status: str = Field(..., alias="targetStatus")
    changed_at_utc: datetime = Field(..., alias="changedAtUtc")

    @classmethod
    def from_record_entry(cls, record_entry: LifecycleHistoryEntry) -> "LifecycleHistoryResponse":
        return cls(
            sourceStatus=record_entry.source_status.value,
            targetStatus=record_entry.target_status.value,
            changedAtUtc=record_entry.changed_at_utc,
        )


class ReviewDecisionSummaryResponse(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    action: str
    resulting_posture: str = Field(..., alias="resultingPosture")
    actor_role: str = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    suppression_reason: str | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, decision: GovernedReviewDecision) -> "ReviewDecisionSummaryResponse":
        return cls(
            reviewId=decision.review_id,
            action=decision.action.value,
            resultingPosture=decision.resulting_posture.value,
            actorRole=decision.actor_role.value,
            reasonCodes=tuple(reason.value for reason in decision.reason_codes),
            decidedAtUtc=decision.decided_at_utc,
            suppressionReason=(
                decision.suppression_reason.value
                if decision.suppression_reason is not None
                else None
            ),
            snoozedUntilUtc=decision.snoozed_until_utc,
            grantsDownstreamAuthority=decision.grants_downstream_authority,
        )


class FeedbackSummaryResponse(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    outcome: str
    actor_role: str = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @classmethod
    def from_domain(cls, event: GovernedFeedbackEvent) -> "FeedbackSummaryResponse":
        return cls(
            feedbackId=event.feedback.feedback_id,
            outcome=event.feedback.outcome.value,
            actorRole=event.actor_role.value,
            reasonCodes=tuple(reason.value for reason in event.feedback.reason_codes),
            recordedAtUtc=event.feedback.recorded_at_utc,
        )


class ConversionIntentSummaryResponse(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: str
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    target_source_authority: str = Field(..., alias="targetSourceAuthority")
    boundary: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, intent: GovernedConversionIntent) -> "ConversionIntentSummaryResponse":
        return cls(
            conversionIntentId=intent.intent.conversion_intent_id,
            target=intent.intent.target.value,
            requestedAtUtc=intent.intent.requested_at_utc,
            targetSourceAuthority=intent.target_source_authority.value,
            boundary=intent.boundary.value,
            reasonCodes=tuple(reason.value for reason in intent.reason_codes),
            grantsDownstreamAuthority=intent.grants_downstream_authority,
        )


class ConversionOutcomeSummaryResponse(CamelModel):
    conversion_outcome_id: str = Field(..., alias="conversionOutcomeId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: str
    status: str
    source_system: str = Field(..., alias="sourceSystem")
    source_event_version: int = Field(..., alias="sourceEventVersion")
    boundary: str
    downstream_reference: str | None = Field(default=None, alias="downstreamReference")
    supersedes_conversion_outcome_id: str | None = Field(
        default=None,
        alias="supersedesConversionOutcomeId",
    )
    correction_reason: str | None = Field(default=None, alias="correctionReason")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")
    grants_execution_authority: bool = Field(False, alias="grantsExecutionAuthority")
    grants_client_communication_authority: bool = Field(
        False, alias="grantsClientCommunicationAuthority"
    )
    grants_suitability_authority: bool = Field(False, alias="grantsSuitabilityAuthority")

    @classmethod
    def from_domain(cls, outcome: GovernedConversionOutcome) -> "ConversionOutcomeSummaryResponse":
        return cls(
            conversionOutcomeId=outcome.outcome.conversion_outcome_id,
            conversionIntentId=outcome.conversion_intent_id,
            target=outcome.target.value,
            status=outcome.outcome.status.value,
            sourceSystem=outcome.source_system.value,
            sourceEventVersion=outcome.source_event_version,
            boundary=outcome.boundary.value,
            downstreamReference=outcome.outcome.downstream_reference,
            supersedesConversionOutcomeId=outcome.supersedes_conversion_outcome_id,
            correctionReason=outcome.correction_reason,
            recordedAtUtc=outcome.outcome.recorded_at_utc,
            grantsExecutionAuthority=outcome.grants_execution_authority,
            grantsClientCommunicationAuthority=outcome.grants_client_communication_authority,
            grantsSuitabilityAuthority=outcome.grants_suitability_authority,
        )


class ReportEvidencePackSummaryResponse(CamelModel):
    report_evidence_pack_id: str = Field(..., alias="reportEvidencePackId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    purpose: str
    boundary: str
    retention_policy_ref: str = Field(..., alias="retentionPolicyRef")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    report_source_authority: str = Field(..., alias="reportSourceAuthority")
    render_source_authority: str = Field(..., alias="renderSourceAuthority")
    archive_source_authority: str = Field(..., alias="archiveSourceAuthority")
    creates_rendered_output: bool = Field(False, alias="createsRenderedOutput")
    creates_archive_record: bool = Field(False, alias="createsArchiveRecord")
    grants_client_publication_authority: bool = Field(
        False, alias="grantsClientPublicationAuthority"
    )

    @classmethod
    def from_domain(cls, pack: GovernedReportEvidencePack) -> "ReportEvidencePackSummaryResponse":
        return cls(
            reportEvidencePackId=pack.report_evidence_pack_id,
            conversionIntentId=pack.conversion_intent_id,
            purpose=pack.purpose.value,
            boundary=pack.boundary.value,
            retentionPolicyRef=pack.retention_policy_ref,
            requestedAtUtc=pack.requested_at_utc,
            reportSourceAuthority=pack.report_source_authority.value,
            renderSourceAuthority=pack.render_source_authority.value,
            archiveSourceAuthority=pack.archive_source_authority.value,
            createsRenderedOutput=pack.creates_rendered_output,
            createsArchiveRecord=pack.creates_archive_record,
            grantsClientPublicationAuthority=pack.grants_client_publication_authority,
        )


class AuditSummaryResponse(CamelModel):
    event_count: int = Field(..., alias="eventCount")
    latest_event_type: str | None = Field(default=None, alias="latestEventType")
    latest_event_outcome: str | None = Field(default=None, alias="latestEventOutcome")
    latest_occurred_at_utc: datetime | None = Field(default=None, alias="latestOccurredAtUtc")

    @classmethod
    def from_record(cls, record: CandidatePersistenceRecord) -> "AuditSummaryResponse":
        latest = record.audit_events[-1] if record.audit_events else None
        return cls(
            eventCount=len(record.audit_events),
            latestEventType=(latest.event_type if latest is not None else None),
            latestEventOutcome=(latest.outcome if latest is not None else None),
            latestOccurredAtUtc=(latest.occurred_at_utc if latest is not None else None),
        )


class CandidateDetailResponse(CamelModel):
    candidate: CandidateDetailCandidateResponse
    evidence: CandidateEvidenceResponse
    lifecycle_history: tuple[LifecycleHistoryResponse, ...] = Field(..., alias="lifecycleHistory")
    review_decisions: tuple[ReviewDecisionSummaryResponse, ...] = Field(
        ..., alias="reviewDecisions"
    )
    feedback_events: tuple[FeedbackSummaryResponse, ...] = Field(..., alias="feedbackEvents")
    conversion_intents: tuple[ConversionIntentSummaryResponse, ...] = Field(
        ..., alias="conversionIntents"
    )
    conversion_outcomes: tuple[ConversionOutcomeSummaryResponse, ...] = Field(
        ..., alias="conversionOutcomes"
    )
    current_conversion_outcomes: tuple[ConversionOutcomeSummaryResponse, ...] = Field(
        ...,
        alias="currentConversionOutcomes",
    )
    report_evidence_packs: tuple[ReportEvidencePackSummaryResponse, ...] = Field(
        ..., alias="reportEvidencePacks"
    )
    audit_summary: AuditSummaryResponse = Field(..., alias="auditSummary")
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_record(
        cls,
        record: CandidatePersistenceRecord,
        *,
        durable_storage_backed: bool = False,
    ) -> "CandidateDetailResponse":
        return cls(
            candidate=CandidateDetailCandidateResponse.from_record(record),
            evidence=CandidateEvidenceResponse.from_record(record),
            lifecycleHistory=tuple(
                LifecycleHistoryResponse.from_record_entry(history_entry)
                for history_entry in record.lifecycle_history
            ),
            reviewDecisions=tuple(
                ReviewDecisionSummaryResponse.from_domain(decision)
                for decision in record.review_decisions
            ),
            feedbackEvents=tuple(
                FeedbackSummaryResponse.from_domain(event) for event in record.feedback_events
            ),
            conversionIntents=tuple(
                ConversionIntentSummaryResponse.from_domain(intent)
                for intent in record.conversion_intents
            ),
            conversionOutcomes=tuple(
                ConversionOutcomeSummaryResponse.from_domain(outcome)
                for outcome in record.conversion_outcomes
            ),
            currentConversionOutcomes=tuple(
                ConversionOutcomeSummaryResponse.from_domain(outcome)
                for outcome in _current_conversion_outcomes(record)
            ),
            reportEvidencePacks=tuple(
                ReportEvidencePackSummaryResponse.from_domain(pack)
                for pack in record.report_evidence_packs
            ),
            auditSummary=AuditSummaryResponse.from_record(record),
            durableStorageBacked=durable_storage_backed,
            supportedFeaturePromoted=False,
        )


def _current_conversion_outcomes(
    record: CandidatePersistenceRecord,
) -> tuple[GovernedConversionOutcome, ...]:
    current: list[GovernedConversionOutcome] = []
    for intent in record.conversion_intents:
        outcome = current_conversion_outcome(
            tuple(
                item
                for item in record.conversion_outcomes
                if item.conversion_intent_id == intent.intent.conversion_intent_id
            )
        )
        if outcome is not None:
            current.append(outcome)
    return tuple(current)


__all__ = (
    "AuditSummaryResponse",
    "CandidateDetailCandidateResponse",
    "CandidateDetailResponse",
    "CandidateEvidenceResponse",
    "ConversionIntentSummaryResponse",
    "ConversionOutcomeSummaryResponse",
    "FeedbackSummaryResponse",
    "LifecycleHistoryResponse",
    "RedactedSourceRefResponse",
    "ReportEvidencePackSummaryResponse",
    "ReviewDecisionSummaryResponse",
)
