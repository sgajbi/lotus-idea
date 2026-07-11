from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, Field

from app.api.base_model import CamelModel
from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryProductPosture,
    RuntimeTrustTelemetryPreview,
)


class RuntimeTrustTelemetryPreviewResponse(CamelModel):
    repository: str
    product_id: str = Field(..., alias="productId")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    candidate_snapshot_count: int = Field(..., alias="candidateSnapshotCount")
    current_source_ref_count: int = Field(..., alias="currentSourceRefCount")
    stale_or_unavailable_source_ref_count: int = Field(
        ...,
        alias="staleOrUnavailableSourceRefCount",
    )
    source_authority_counts: Mapping[str, int] = Field(..., alias="sourceAuthorityCounts")
    freshness_counts: Mapping[str, int] = Field(..., alias="freshnessCounts")
    supportability_counts: Mapping[str, int] = Field(..., alias="supportabilityCounts")
    lifecycle_counts: Mapping[str, int] = Field(..., alias="lifecycleCounts")
    data_lifecycle_state_counts: Mapping[str, int] = Field(..., alias="dataLifecycleStateCounts")
    retention_expired_count: int = Field(..., alias="retentionExpiredCount")
    lifecycle_control_missing_count: int = Field(..., alias="lifecycleControlMissingCount")
    review_decision_count: int = Field(..., alias="reviewDecisionCount")
    feedback_event_count: int = Field(..., alias="feedbackEventCount")
    conversion_intent_count: int = Field(..., alias="conversionIntentCount")
    conversion_outcome_count: int = Field(..., alias="conversionOutcomeCount")
    report_evidence_pack_count: int = Field(..., alias="reportEvidencePackCount")
    lineage_materialized: bool = Field(..., alias="lineageMaterialized")
    runtime_telemetry_backed: bool = Field(..., alias="runtimeTelemetryBacked")
    platform_certified: bool = Field(..., alias="platformCertified")
    certification_status: str = Field(..., alias="certificationStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")
    product_coverage: tuple["RuntimeTrustTelemetryProductPostureResponse", ...] = Field(
        ...,
        alias="productCoverage",
    )

    @classmethod
    def from_domain(
        cls,
        snapshot: RuntimeTrustTelemetryPreview,
    ) -> "RuntimeTrustTelemetryPreviewResponse":
        return cls(
            repository=snapshot.repository,
            productId=snapshot.product_id,
            generatedAtUtc=snapshot.generated_at_utc,
            candidateSnapshotCount=snapshot.candidate_snapshot_count,
            currentSourceRefCount=snapshot.current_source_ref_count,
            staleOrUnavailableSourceRefCount=snapshot.stale_or_unavailable_source_ref_count,
            sourceAuthorityCounts=dict(snapshot.source_authority_counts),
            freshnessCounts=dict(snapshot.freshness_counts),
            supportabilityCounts=dict(snapshot.supportability_counts),
            lifecycleCounts=dict(snapshot.lifecycle_counts),
            dataLifecycleStateCounts=dict(snapshot.data_lifecycle_state_counts),
            retentionExpiredCount=snapshot.retention_expired_count,
            lifecycleControlMissingCount=snapshot.lifecycle_control_missing_count,
            reviewDecisionCount=snapshot.review_decision_count,
            feedbackEventCount=snapshot.feedback_event_count,
            conversionIntentCount=snapshot.conversion_intent_count,
            conversionOutcomeCount=snapshot.conversion_outcome_count,
            reportEvidencePackCount=snapshot.report_evidence_pack_count,
            lineageMaterialized=snapshot.lineage_materialized,
            runtimeTelemetryBacked=snapshot.runtime_telemetry_backed,
            platformCertified=snapshot.platform_certified,
            certificationStatus=snapshot.certification_status,
            certificationReady=snapshot.certification_ready,
            certificationBlockers=snapshot.certification_blockers,
            productCoverage=tuple(
                RuntimeTrustTelemetryProductPostureResponse.from_domain(posture)
                for posture in snapshot.product_postures
            ),
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class RuntimeTrustTelemetryProductPostureResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    product_name: str = Field(..., alias="productName")
    product_version: str = Field(..., alias="productVersion")
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    freshness_class: str = Field(..., alias="freshnessClass")
    coverage_status: str = Field(..., alias="coverageStatus")
    runtime_backed: bool = Field(..., alias="runtimeBacked")
    observed_record_count: int = Field(..., alias="observedRecordCount")
    current_source_ref_count: int = Field(..., alias="currentSourceRefCount")
    stale_or_unavailable_source_ref_count: int = Field(
        ...,
        alias="staleOrUnavailableSourceRefCount",
    )
    freshness_state: str = Field(..., alias="freshnessState")
    completeness_status: str = Field(..., alias="completenessStatus")
    reconciliation_status: str = Field(..., alias="reconciliationStatus")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    lineage_materialized: bool = Field(..., alias="lineageMaterialized")
    source_batch_evidence_available: bool = Field(..., alias="sourceBatchEvidenceAvailable")
    consumer_exposure_status: str = Field(..., alias="consumerExposureStatus")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")

    @classmethod
    def from_domain(
        cls,
        posture: RuntimeTrustTelemetryProductPosture,
    ) -> "RuntimeTrustTelemetryProductPostureResponse":
        return cls(
            productId=posture.product_id,
            productName=posture.product_name,
            productVersion=posture.product_version,
            lifecycleStatus=posture.lifecycle_status,
            freshnessClass=posture.freshness_class,
            coverageStatus=posture.coverage_status,
            runtimeBacked=posture.runtime_backed,
            observedRecordCount=posture.observed_record_count,
            currentSourceRefCount=posture.current_source_ref_count,
            staleOrUnavailableSourceRefCount=posture.stale_or_unavailable_source_ref_count,
            freshnessState=posture.freshness_state,
            completenessStatus=posture.completeness_status,
            reconciliationStatus=posture.reconciliation_status,
            dataQualityStatus=posture.data_quality_status,
            lineageMaterialized=posture.lineage_materialized,
            sourceBatchEvidenceAvailable=posture.source_batch_evidence_available,
            consumerExposureStatus=posture.consumer_exposure_status,
            certificationBlockers=posture.certification_blockers,
        )


class RuntimeTrustTelemetryFreshnessResponse(BaseModel):
    freshness_class: str
    freshness_state: str
    evaluated_at_utc: str
    age_seconds: int | None = None
    max_allowed_age_seconds: int | None = None


class RuntimeTrustTelemetryLineageResponse(BaseModel):
    lineage_materialized: bool
    evidence_access_class: str
    evidence_uris: list[str]


class RuntimeTrustTelemetryDataLifecycleResponse(BaseModel):
    state_counts: Mapping[str, int]
    retention_expired_count: int
    lifecycle_control_missing_count: int
    certification_status: str
    supported_feature_promoted: bool


class RuntimeTrustTelemetryBlockingResponse(BaseModel):
    blocked: bool
    blocked_reason: str


class RuntimeTrustTelemetryEvidenceResponse(BaseModel):
    correlation_id: str
    validation_lanes: list[str]
    source_artifact_uri: str


class RuntimeTrustTelemetryProductCoverageSnapshotResponse(BaseModel):
    product_id: str
    product_name: str
    product_version: str
    lifecycle_status: str
    freshness_class: str
    coverage_status: str
    runtime_backed: bool
    observed_record_count: int
    current_source_ref_count: int
    stale_or_unavailable_source_ref_count: int
    freshness_state: str
    completeness_status: str
    reconciliation_status: str
    data_quality_status: str
    lineage_materialized: bool
    source_batch_evidence_available: bool
    consumer_exposure_status: str
    certification_blockers: list[str]


class RuntimeTrustTelemetrySnapshotResponse(BaseModel):
    contract_id: str
    contract_version: str
    governed_by_rfcs: list[str]
    emitted_at_utc: str
    product_id: str
    producer_repository: str
    product_name: str
    product_version: str
    source_repository: str
    freshness: RuntimeTrustTelemetryFreshnessResponse
    completeness_status: str
    reconciliation_status: str
    data_quality_status: str
    lineage: RuntimeTrustTelemetryLineageResponse
    data_lifecycle: RuntimeTrustTelemetryDataLifecycleResponse
    blocking: RuntimeTrustTelemetryBlockingResponse
    product_coverage: list[RuntimeTrustTelemetryProductCoverageSnapshotResponse]
    observed_trust_metadata: Mapping[str, str]
    evidence: RuntimeTrustTelemetryEvidenceResponse

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RuntimeTrustTelemetrySnapshotResponse":
        return cls(**payload)


__all__ = [
    "RuntimeTrustTelemetryBlockingResponse",
    "RuntimeTrustTelemetryDataLifecycleResponse",
    "RuntimeTrustTelemetryEvidenceResponse",
    "RuntimeTrustTelemetryFreshnessResponse",
    "RuntimeTrustTelemetryLineageResponse",
    "RuntimeTrustTelemetryPreviewResponse",
    "RuntimeTrustTelemetryProductCoverageSnapshotResponse",
    "RuntimeTrustTelemetryProductPostureResponse",
    "RuntimeTrustTelemetrySnapshotResponse",
]
