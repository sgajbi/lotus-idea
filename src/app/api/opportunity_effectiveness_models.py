from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.opportunity_effectiveness import OpportunityEffectivenessSnapshot


class EffectivenessWindowResponse(CamelModel):
    start_utc_inclusive: datetime = Field(..., alias="startUtcInclusive")
    end_utc_exclusive: datetime = Field(..., alias="endUtcExclusive")
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    population: str
    outcome_observation: str = Field(..., alias="outcomeObservation")


class EffectivenessCountsResponse(CamelModel):
    generated_opportunity_count: int = Field(..., alias="generatedOpportunityCount")
    reviewed_opportunity_count: int = Field(..., alias="reviewedOpportunityCount")
    feedback_opportunity_count: int = Field(..., alias="feedbackOpportunityCount")
    conversion_opportunity_count: int = Field(..., alias="conversionOpportunityCount")
    conversion_intent_count: int = Field(..., alias="conversionIntentCount")
    stale_evidence_opportunity_count: int = Field(..., alias="staleEvidenceOpportunityCount")
    unavailable_evidence_opportunity_count: int = Field(
        ..., alias="unavailableEvidenceOpportunityCount"
    )
    unsupported_evidence_opportunity_count: int = Field(
        ..., alias="unsupportedEvidenceOpportunityCount"
    )
    suppressed_opportunity_count: int = Field(..., alias="suppressedOpportunityCount")
    duplicate_suppressed_opportunity_count: int = Field(
        ..., alias="duplicateSuppressedOpportunityCount"
    )
    recurrent_opportunity_count: int = Field(..., alias="recurrentOpportunityCount")
    recurrent_detection_count: int = Field(..., alias="recurrentDetectionCount")
    reconciled_submission_count: int = Field(..., alias="reconciledSubmissionCount")


class EffectivenessPresentationResponse(CamelModel):
    measurement_status: str = Field(..., alias="measurementStatus")
    presented_opportunity_count: int | None = Field(..., alias="presentedOpportunityCount")
    top_ranked_presented_opportunity_count: int | None = Field(
        ..., alias="topRankedPresentedOpportunityCount"
    )
    top_ranked_accepted_opportunity_count: int | None = Field(
        ..., alias="topRankedAcceptedOpportunityCount"
    )
    presentation_rate: EffectivenessRateResponse | None = Field(..., alias="presentationRate")
    top_ranked_acceptance_rate: EffectivenessRateResponse | None = Field(
        ..., alias="topRankedAcceptanceRate"
    )


class EffectivenessDimensionCountResponse(CamelModel):
    value: str
    count: int


class EffectivenessDimensionsResponse(CamelModel):
    opportunity_family: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="opportunityFamily"
    )
    current_score_band: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="currentScoreBand"
    )
    latest_review_action: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="latestReviewAction"
    )
    feedback_reason: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="feedbackReason"
    )
    current_downstream_outcome: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="currentDownstreamOutcome"
    )
    downstream_submission_posture: tuple[EffectivenessDimensionCountResponse, ...] = Field(
        ..., alias="downstreamSubmissionPosture"
    )


class EffectivenessRateResponse(CamelModel):
    numerator: int
    denominator: int
    value: Decimal | None
    zero_denominator_behavior: str = Field(..., alias="zeroDenominatorBehavior")


class EffectivenessRatesResponse(CamelModel):
    review: EffectivenessRateResponse
    approval: EffectivenessRateResponse
    rejection: EffectivenessRateResponse
    suppression: EffectivenessRateResponse
    feedback: EffectivenessRateResponse
    conversion: EffectivenessRateResponse
    downstream_accepted: EffectivenessRateResponse = Field(..., alias="downstreamAccepted")
    downstream_rejected: EffectivenessRateResponse = Field(..., alias="downstreamRejected")
    downstream_uncertain: EffectivenessRateResponse = Field(..., alias="downstreamUncertain")


class EffectivenessDurationResponse(CamelModel):
    observation_count: int = Field(..., alias="observationCount")
    minimum_seconds: Decimal | None = Field(..., alias="minimumSeconds")
    p50_seconds: Decimal | None = Field(..., alias="p50Seconds")
    p95_seconds: Decimal | None = Field(..., alias="p95Seconds")
    maximum_seconds: Decimal | None = Field(..., alias="maximumSeconds")


class EffectivenessTimingsResponse(CamelModel):
    detection_to_review: EffectivenessDurationResponse = Field(..., alias="detectionToReview")
    approval_to_conversion: EffectivenessDurationResponse = Field(..., alias="approvalToConversion")


class EffectivenessPrivacyBoundaryResponse(CamelModel):
    scope: str
    contains_raw_tenant_identifier: bool = Field(..., alias="containsRawTenantIdentifier")
    contains_raw_client_identifier: bool = Field(..., alias="containsRawClientIdentifier")
    contains_raw_portfolio_identifier: bool = Field(..., alias="containsRawPortfolioIdentifier")
    contains_raw_candidate_identifier: bool = Field(..., alias="containsRawCandidateIdentifier")
    contains_business_identity_identifier: bool = Field(
        ..., alias="containsBusinessIdentityIdentifier"
    )
    contains_actor_subject: bool = Field(..., alias="containsActorSubject")
    contains_correlation_or_trace_identifier: bool = Field(
        ..., alias="containsCorrelationOrTraceIdentifier"
    )
    contains_free_text: bool = Field(..., alias="containsFreeText")


class OpportunityEffectivenessResponse(CamelModel):
    schema_version: str = Field(..., alias="schemaVersion")
    methodology_policy_version: str = Field(..., alias="methodologyPolicyVersion")
    window: EffectivenessWindowResponse
    counts: EffectivenessCountsResponse
    presentation: EffectivenessPresentationResponse
    dimensions: EffectivenessDimensionsResponse
    rates: EffectivenessRatesResponse
    timings: EffectivenessTimingsResponse
    privacy_boundary: EffectivenessPrivacyBoundaryResponse = Field(..., alias="privacyBoundary")
    certification_status: str = Field(..., alias="certificationStatus")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")
    production_mutation_authority: str = Field(..., alias="productionMutationAuthority")
    snapshot_digest: str = Field(..., alias="snapshotDigest")

    @classmethod
    def from_domain(
        cls,
        snapshot: OpportunityEffectivenessSnapshot,
    ) -> OpportunityEffectivenessResponse:
        return cls.model_validate(snapshot.to_payload())


__all__ = ["OpportunityEffectivenessResponse"]
