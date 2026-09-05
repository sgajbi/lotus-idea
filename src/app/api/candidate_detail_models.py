from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.api.downstream_owner_receipt_models import DownstreamOwnerReceiptResponse
from app.api.score_models import ScoreContributionResponse
from app.api.signal_models import CandidateIdentityResponse
from app.domain import (
    CandidatePersistenceRecord,
    CandidateVersionHistoryEntry,
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    GovernedFeedbackEvent,
    GovernedReportEvidencePack,
    GovernedReviewDecision,
    IdeaCandidate,
    LifecycleHistoryEntry,
    SourceRef,
    SourceSystem,
    current_conversion_outcome,
)


class CandidateDetailCandidateResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    identity: CandidateIdentityResponse
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    supportability: str
    score: str | None = None
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    score_reason_codes: tuple[str, ...] = Field(..., alias="scoreReasonCodes")
    score_components: tuple[ScoreContributionResponse, ...] = Field(..., alias="scoreComponents")
    score_conflict_penalty_applied: str | None = Field(
        default=None,
        alias="scoreConflictPenaltyApplied",
    )
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    suppression_reason: str | None = Field(default=None, alias="suppressionReason")
    created_at_utc: datetime = Field(..., alias="createdAtUtc")
    updated_at_utc: datetime = Field(..., alias="updatedAtUtc")
    applicability_expires_at_utc: datetime | None = Field(
        default=None,
        alias="applicabilityExpiresAtUtc",
    )

    @classmethod
    def from_record(cls, record: CandidatePersistenceRecord) -> "CandidateDetailCandidateResponse":
        candidate = record.candidate
        score = candidate.score
        return cls(
            candidateId=candidate.candidate_id,
            identity=CandidateIdentityResponse.from_domain(candidate.identity),
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            supportability=candidate.evidence_packet.supportability.value,
            score=(str(score.score) if score is not None else None),
            scorePolicyVersion=(score.policy_version if score is not None else None),
            scoreReasonCodes=(
                tuple(reason.value for reason in score.reason_codes) if score is not None else ()
            ),
            scoreComponents=(
                tuple(ScoreContributionResponse.from_domain(item) for item in score.contributions)
                if score is not None
                else ()
            ),
            scoreConflictPenaltyApplied=(
                str(score.conflict_penalty_applied) if score is not None else None
            ),
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
            applicabilityExpiresAtUtc=(candidate.evidence_packet.applicability_expires_at_utc),
        )


class CandidateVersionHistoryResponse(CamelModel):
    material_version: int = Field(..., alias="materialVersion")
    evidence_version: int = Field(..., alias="evidenceVersion")
    change_reason: str = Field(..., alias="changeReason")
    source_lifecycle_status: str | None = Field(default=None, alias="sourceLifecycleStatus")
    resulting_lifecycle_status: str = Field(..., alias="resultingLifecycleStatus")
    supersedes_material_version: int | None = Field(
        default=None,
        alias="supersedesMaterialVersion",
    )
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @classmethod
    def from_domain(
        cls,
        entry: CandidateVersionHistoryEntry,
    ) -> "CandidateVersionHistoryResponse":
        return cls(
            materialVersion=entry.material_version,
            evidenceVersion=entry.evidence_version,
            changeReason=entry.change_reason.value,
            sourceLifecycleStatus=(
                entry.source_lifecycle_status.value
                if entry.source_lifecycle_status is not None
                else None
            ),
            resultingLifecycleStatus=entry.resulting_lifecycle_status.value,
            supersedesMaterialVersion=entry.supersedes_material_version,
            recordedAtUtc=entry.recorded_at_utc,
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
    applicability_expires_at_utc: datetime | None = Field(
        default=None,
        alias="applicabilityExpiresAtUtc",
    )

    @classmethod
    def from_record(cls, record: CandidatePersistenceRecord) -> "CandidateEvidenceResponse":
        evidence_packet = record.candidate.evidence_packet
        return cls(
            evidencePacketId=evidence_packet.evidence_packet_id,
            evidenceContentHash=evidence_packet.lineage_ref.content_hash,
            supportability=evidence_packet.supportability.value,
            lineageId=evidence_packet.lineage_ref.lineage_id,
            createdAtUtc=evidence_packet.created_at_utc,
            sourceRefs=tuple(
                RedactedSourceRefResponse.from_domain(source_ref)
                for source_ref in evidence_packet.source_refs
            ),
            applicabilityExpiresAtUtc=evidence_packet.applicability_expires_at_utc,
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
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    candidate_material_version: int = Field(..., alias="candidateMaterialVersion")
    candidate_evidence_version: int = Field(..., alias="candidateEvidenceVersion")
    review_channel: str = Field(..., alias="reviewChannel")
    presentation_receipt_id: str | None = Field(default=None, alias="presentationReceiptId")
    queue_snapshot_digest: str | None = Field(default=None, alias="queueSnapshotDigest")
    review_policy_version: str = Field(..., alias="reviewPolicyVersion")
    authority_policy_version: str = Field(..., alias="authorityPolicyVersion")
    action: str
    resulting_posture: str = Field(..., alias="resultingPosture")
    actor_role: str = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    accepted_at_utc: datetime = Field(..., alias="acceptedAtUtc")
    applicability_expires_at_utc: datetime | None = Field(
        default=None,
        alias="applicabilityExpiresAtUtc",
    )
    authority_status: str | None = Field(default=None, alias="authorityStatus")
    suppression_reason: str | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(
        cls,
        decision: GovernedReviewDecision,
        *,
        candidate: IdeaCandidate,
        evaluated_at_utc: datetime,
    ) -> "ReviewDecisionSummaryResponse":
        grant = decision.authority_grant
        return cls(
            reviewId=decision.review_id,
            evidencePacketId=decision.evidence_packet_id,
            evidenceContentHash=decision.evidence_content_hash,
            candidateMaterialVersion=decision.candidate_material_version,
            candidateEvidenceVersion=decision.candidate_evidence_version,
            reviewChannel=decision.review_channel.value,
            presentationReceiptId=decision.presentation_receipt_id,
            queueSnapshotDigest=decision.queue_snapshot_digest,
            reviewPolicyVersion=decision.review_policy_version,
            authorityPolicyVersion=decision.review_authority_policy_version,
            action=decision.action.value,
            resultingPosture=decision.resulting_posture.value,
            actorRole=decision.actor_role.value,
            reasonCodes=tuple(reason.value for reason in decision.reason_codes),
            decidedAtUtc=decision.decided_at_utc,
            acceptedAtUtc=decision.accepted_at_utc,
            applicabilityExpiresAtUtc=decision.applicability_expires_at_utc,
            authorityStatus=(
                grant.effective_status(candidate, evaluated_at_utc=evaluated_at_utc).value
                if grant is not None
                else None
            ),
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
    taxonomy_version: str = Field(..., alias="taxonomyVersion")
    outcome: str
    reason: str
    actor_role: str = Field(..., alias="actorRole")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @classmethod
    def from_domain(cls, event: GovernedFeedbackEvent) -> "FeedbackSummaryResponse":
        return cls(
            feedbackId=event.feedback.feedback_id,
            taxonomyVersion=event.feedback.taxonomy_version,
            outcome=event.feedback.outcome.value,
            reason=event.feedback.reason.value,
            actorRole=event.actor_role.value,
            recordedAtUtc=event.feedback.recorded_at_utc,
        )


class ConversionIntentSummaryResponse(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: str
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    target_source_authority: str = Field(..., alias="targetSourceAuthority")
    boundary: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    accepted_at_utc: datetime = Field(..., alias="acceptedAtUtc")
    review_id: str | None = Field(default=None, alias="reviewId")
    review_channel: str | None = Field(default=None, alias="reviewChannel")
    review_policy_version: str | None = Field(default=None, alias="reviewPolicyVersion")
    authority_policy_version: str | None = Field(default=None, alias="authorityPolicyVersion")
    presentation_receipt_id: str | None = Field(default=None, alias="presentationReceiptId")
    candidate_material_version: int | None = Field(default=None, alias="candidateMaterialVersion")
    candidate_evidence_version: int | None = Field(default=None, alias="candidateEvidenceVersion")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, intent: GovernedConversionIntent) -> "ConversionIntentSummaryResponse":
        grant = intent.review_authority_grant
        return cls(
            conversionIntentId=intent.intent.conversion_intent_id,
            target=intent.intent.target.value,
            requestedAtUtc=intent.intent.requested_at_utc,
            targetSourceAuthority=intent.target_source_authority.value,
            boundary=intent.boundary.value,
            reasonCodes=tuple(reason.value for reason in intent.reason_codes),
            acceptedAtUtc=intent.accepted_at_utc,
            reviewId=grant.review_id if grant is not None else None,
            reviewChannel=grant.review_channel.value if grant is not None else None,
            reviewPolicyVersion=grant.review_policy_version if grant is not None else None,
            authorityPolicyVersion=(grant.authority_policy_version if grant is not None else None),
            presentationReceiptId=grant.presentation_receipt_id if grant is not None else None,
            candidateMaterialVersion=(
                grant.candidate_evidence.material_version if grant is not None else None
            ),
            candidateEvidenceVersion=(
                grant.candidate_evidence.evidence_version if grant is not None else None
            ),
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


class DownstreamSubmissionSummaryResponse(CamelModel):
    resource_type: DownstreamSubmissionResourceType = Field(
        ...,
        alias="resourceType",
        description="Idea-owned resource whose delivery posture is shown.",
    )
    resource_id: str = Field(
        ...,
        alias="resourceId",
        min_length=1,
        description="Identifier of the candidate-linked conversion intent or report pack.",
    )
    target: ConversionTarget = Field(
        ...,
        description="Downstream workflow requested by the Idea-owned resource.",
    )
    source_authority: SourceSystem = Field(
        ...,
        alias="sourceAuthority",
        description="System that owns authoritative realization outcomes.",
    )
    submission_posture: DownstreamSubmissionPosture = Field(
        ...,
        alias="submissionPosture",
        description="Idea-owned local delivery posture; not a business outcome.",
    )
    submitted_at_utc: datetime = Field(
        ...,
        alias="submittedAtUtc",
        description="UTC time when Idea first claimed the downstream submission.",
    )
    updated_at_utc: datetime = Field(
        ...,
        alias="updatedAtUtc",
        description="UTC time when the local submission posture last changed.",
    )
    attempt_count: int = Field(
        ...,
        alias="attemptCount",
        ge=1,
        description="Number of locally claimed delivery attempts.",
    )
    operator_reconciliation_required: bool = Field(
        ...,
        alias="operatorReconciliationRequired",
        description="True only when the local posture explicitly requires reconciliation.",
    )
    records_downstream_outcome: bool = Field(
        ...,
        alias="recordsDownstreamOutcome",
        description="Always false; source-owned outcomes are recorded separately.",
    )
    grants_downstream_authority: bool = Field(
        ...,
        alias="grantsDownstreamAuthority",
        description="Always false; local delivery posture grants no downstream authority.",
    )
    owner_receipt: DownstreamOwnerReceiptResponse | None = Field(
        default=None,
        alias="ownerReceipt",
        description="Exact owner acknowledgement; it is not an Idea-owned business outcome.",
    )

    @classmethod
    def from_domain(
        cls,
        submission: DownstreamSubmissionRecord,
    ) -> "DownstreamSubmissionSummaryResponse":
        return cls(
            resourceType=submission.resource_type,
            resourceId=submission.resource_id,
            target=submission.target,
            sourceAuthority=submission.source_authority,
            submissionPosture=submission.status,
            submittedAtUtc=submission.submitted_at_utc,
            updatedAtUtc=submission.updated_at_utc,
            attemptCount=submission.attempt_count,
            operatorReconciliationRequired=(
                submission.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
            ),
            recordsDownstreamOutcome=False,
            grantsDownstreamAuthority=False,
            ownerReceipt=(
                DownstreamOwnerReceiptResponse.from_domain(submission.owner_receipt)
                if submission.owner_receipt is not None
                else None
            ),
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
    version_history: tuple[CandidateVersionHistoryResponse, ...] = Field(
        ...,
        alias="versionHistory",
    )
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
    downstream_submissions: tuple[DownstreamSubmissionSummaryResponse, ...] = Field(
        ...,
        alias="downstreamSubmissions",
    )
    audit_summary: AuditSummaryResponse = Field(..., alias="auditSummary")
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_record(
        cls,
        record: CandidatePersistenceRecord,
        *,
        downstream_submissions: tuple[DownstreamSubmissionRecord, ...] = (),
        durable_storage_backed: bool = False,
        evaluated_at_utc: datetime | None = None,
    ) -> "CandidateDetailResponse":
        if record.review_decisions and evaluated_at_utc is None:
            raise ValueError("evaluated_at_utc is required when projecting review authority")
        authority_evaluated_at = evaluated_at_utc or record.candidate.updated_at_utc
        return cls(
            candidate=CandidateDetailCandidateResponse.from_record(record),
            versionHistory=tuple(
                CandidateVersionHistoryResponse.from_domain(entry)
                for entry in record.version_history
            ),
            evidence=CandidateEvidenceResponse.from_record(record),
            lifecycleHistory=tuple(
                LifecycleHistoryResponse.from_record_entry(history_entry)
                for history_entry in record.lifecycle_history
            ),
            reviewDecisions=tuple(
                ReviewDecisionSummaryResponse.from_domain(
                    decision,
                    candidate=record.candidate,
                    evaluated_at_utc=authority_evaluated_at,
                )
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
            downstreamSubmissions=tuple(
                DownstreamSubmissionSummaryResponse.from_domain(submission)
                for submission in downstream_submissions
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
    "DownstreamSubmissionSummaryResponse",
    "FeedbackSummaryResponse",
    "LifecycleHistoryResponse",
    "RedactedSourceRefResponse",
    "ReportEvidencePackSummaryResponse",
    "ReviewDecisionSummaryResponse",
)
